from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

from pandas import DataFrame

from basis.core.component import ComponentType, ComponentUri
from basis.core.data_block import DataBlockMetadata, DataSetMetadata
from basis.core.data_format import DatabaseTable, DictList
from basis.core.data_function_interface import DataFunctionInterface
from basis.core.module import DEFAULT_LOCAL_MODULE, BasisModule
from basis.core.runtime import RuntimeClass

if TYPE_CHECKING:
    from basis.core.runnable import DataFunctionContext


class DataFunctionException(Exception):
    pass


class InputExhaustedException(DataFunctionException):
    pass


DataFunctionCallable = Callable[..., Any]

DataInterfaceType = Union[
    DataFrame, DictList, DatabaseTable, DataBlockMetadata, DataSetMetadata
]  # TODO: also input...?   Isn't this duplicated with the Interface list AND with DataFormats?


def get_runtime_class(runtime: Optional[str]) -> RuntimeClass:
    if runtime is None:
        return RuntimeClass.PYTHON
    if (
        "ql" in runtime.lower()
        or "database" in runtime.lower()
        or "postgre" in runtime.lower()
    ):
        return RuntimeClass.DATABASE
    return RuntimeClass.PYTHON


def make_datafunction_name(data_function: DataFunctionCallable) -> str:
    # TODO: something more principled / explicit?
    if hasattr(data_function, "name"):
        return data_function.name  # type: ignore
    if hasattr(data_function, "__name__"):
        return data_function.__name__
    if hasattr(data_function, "__class__"):
        return data_function.__class__.__name__
    raise Exception(f"Invalid DataFunction name {data_function}")


@dataclass(frozen=True)
class DataFunction(ComponentUri):
    # component_type = ComponentType.DataFunction
    runtime_data_functions: Dict[RuntimeClass, DataFunctionDefinition] = field(
        default_factory=dict
    )

    def __call__(
        self, *args: DataFunctionContext, **kwargs: DataInterfaceType
    ) -> Optional[DataInterfaceType]:
        raise NotImplementedError
        # # TODO: hack, but maybe useful to have actual DataFunction still act like a function
        # for v in self.runtime_data_functions.values():
        #     try:
        #         return v(*args, **kwargs)
        #     except:
        #         pass

    def get_representative_definition(self) -> DataFunctionDefinition:
        return list(self.runtime_data_functions.values())[0]

    def get_interface(self) -> Optional[DataFunctionInterface]:
        dfd = self.get_representative_definition()
        if not dfd:
            raise
        return dfd.get_interface()

    def add_definition(self, df: DataFunctionDefinition):
        for cls in df.supported_runtime_classes:
            self.runtime_data_functions[cls] = df

    def validate(self):
        # TODO: check if all function signatures match
        pass

    def merge(self, other: DataFunction, overwrite: bool = False):
        for cls, df in other.runtime_data_functions.items():
            if cls not in self.runtime_data_functions:
                self.runtime_data_functions[cls] = df

    def get_definition(
        self, runtime_cls: RuntimeClass
    ) -> Optional[DataFunctionDefinition]:
        return self.runtime_data_functions.get(runtime_cls)

    def associate_with_module(self, module: BasisModule) -> ComponentUri:
        dfds: Dict[RuntimeClass, DataFunctionDefinition] = {}
        for cls, dfd in self.runtime_data_functions.items():
            dfds[cls] = dfd.associate_with_module(module)
        return self.clone(module_name=module.name, runtime_data_functions=dfds)


@dataclass(frozen=True)
class DataFunctionDefinition(ComponentUri):
    # component_type = ComponentType.DataFunction
    function_callable: Optional[
        Callable
    ]  # Optional since Composite DFs don't have a Callable
    supported_runtime_classes: List[RuntimeClass]
    is_composite: bool = False
    configuration_class: Optional[Type] = None
    sub_functions: List[ComponentUri] = field(
        default_factory=list
    )  # TODO: support proper graphs
    # TODO: runtime engine eg "mysql>=8.0", "python==3.7.4"  ???
    # TODO: runtime dependencies

    def __call__(
        self, *args: DataFunctionContext, **kwargs: DataInterfaceType
    ) -> Optional[DataInterfaceType]:
        if self.is_composite:
            raise NotImplementedError(f"Cannot call a composite DataFunction {self}")
        if self.function_callable is None:
            raise
        return self.function_callable(*args, **kwargs)

    def get_interface(self) -> Optional[DataFunctionInterface]:
        if self.function_callable is None:
            assert self.is_composite
            return None
        if hasattr(self.function_callable, "get_interface"):
            return self.function_callable.get_interface()
        return DataFunctionInterface.from_datafunction_definition(
            self.function_callable
        )

    def associate_with_module(self, module: BasisModule) -> ComponentUri:
        new_subs = []
        if self.sub_functions:
            for sub in self.sub_functions:
                new_subs.append(sub.associate_with_module(module))
        return self.clone(module_name=module.name, sub_functions=new_subs)

    def as_data_function(self) -> DataFunction:
        df = DataFunction(
            component_type=ComponentType.DataFunction,
            name=self.name,
            module_name=self.module_name,
            version=self.version,
        )
        df.add_definition(self)
        return df


DataFunctionDefinitionLike = Union[DataFunctionCallable, DataFunctionDefinition]
DataFunctionLike = Union[DataFunctionCallable, DataFunctionDefinition, DataFunction]


def data_function_definition_factory(
    function_callable: Optional[
        DataFunctionCallable
    ],  # Composite DFs don't have a callable
    name: str = None,
    version: str = None,
    supported_runtimes: str = None,
    module_name: str = None,
    **kwargs: Any,
) -> DataFunctionDefinition:
    if name is None:
        if function_callable is None:
            raise
        name = make_datafunction_name(function_callable)
    runtime_class = get_runtime_class(supported_runtimes)
    return DataFunctionDefinition(
        component_type=ComponentType.DataFunction,
        name=name,
        module_name=module_name,
        version=version,
        function_callable=function_callable,
        supported_runtime_classes=[runtime_class],
        **kwargs,
    )


def datafunction(
    df_or_name: Union[str, DataFunctionCallable] = None,
    name: str = None,
    version: str = None,
    supported_runtimes: str = None,
    module_name: str = None,
    # test_data: DataFunctionTestCaseLike = None,
) -> Union[Callable, DataFunctionDefinition]:
    if isinstance(df_or_name, str) or df_or_name is None:
        return partial(
            datafunction,
            name=df_or_name,
            version=version,
            supported_runtimes=supported_runtimes,
            module_name=module_name,
        )
    return data_function_definition_factory(
        df_or_name,
        name=name,
        version=version,
        supported_runtimes=supported_runtimes,
        module_name=module_name,
    )


def datafunction_chain(
    name: str, function_chain: List[Union[DataFunctionLike, str]], **kwargs
) -> DataFunctionDefinition:
    sub_funcs = []
    for fn in function_chain:
        if isinstance(fn, str):
            uri = ComponentUri.from_str(fn, component_type=ComponentType.DataFunction)
        elif isinstance(fn, ComponentUri):
            uri = fn
        elif callable(fn):
            uri = ensure_datafunction_definition(fn, **kwargs)
        else:
            raise TypeError(f"Invalid function uri in chain {fn}")
        sub_funcs.append(uri)
    return data_function_definition_factory(
        None, name=name, sub_functions=sub_funcs, is_composite=True, **kwargs
    )


def ensure_datafunction_definition(
    dfl: DataFunctionLike, **kwargs
) -> DataFunctionDefinition:
    if isinstance(dfl, DataFunctionDefinition):
        return dfl
    return data_function_definition_factory(dfl, **kwargs)


def ensure_datafunction(dfl: DataFunctionLike, **kwargs) -> DataFunction:
    if isinstance(dfl, DataFunction):
        return dfl
    dfd = ensure_datafunction_definition(dfl, **kwargs)
    return dfd.as_data_function()