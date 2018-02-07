import typing
import types
import inspect
import collections

from .exceptions import NeuroLangException


class NeuroLangTypeException(NeuroLangException):
    pass


def typing_callable_from_annotated_function(function):
    signature = inspect.signature(function)
    parameter_types = [
        v.annotation for v in signature.parameters.values()
    ]
    return typing.Callable[
        parameter_types,
        signature.return_annotation
    ]


def get_type_args(type_):
    if hasattr(type_, '__args__') and type_.__args__ is not None:
        return type_.__args__
    else:
        return tuple()


def is_subtype(left, right):
    if right == typing.Any:
        return True
    elif hasattr(right, '__origin__'):
        if right.__origin__ == typing.Union:
            return any(
                is_subtype(left, r)
                for r in right.__args__
            )
        elif issubclass(right, typing.Callable):
            if issubclass(left, typing.Callable):
                left_args = get_type_args(left)
                right_args = get_type_args(right)

                if len(left_args) != len(right_args):
                    False

                return all((
                    is_subtype(left_arg, right_arg)
                    for left_arg, right_arg in zip(left_args, right_args)
                ))
            else:
                return False
        elif (any(
            issubclass(right, T) and
            issubclass(left, T)
            for T in (
                typing.AbstractSet, typing.List, typing.Tuple,
                typing.Mapping, typing.Iterable
            )
        )):
            return all(
                is_subtype(l, r) for l, r in zip(
                    get_type_args(left), get_type_args(right)
                )
            )
        else:
            raise ValueError("typing Generic not supported")
    else:
        if right == int:
            right = typing.SupportsInt
        elif right == float:
            right = typing.SupportsFloat
        elif right == str:
            right = typing.Text

        return issubclass(left, right)


def replace_type_variable(type_, type_hint, type_var=None):
    if (
        isinstance(type_hint, typing.TypeVar) and
        type_hint == type_var
    ):
        return type_
    elif hasattr(type_hint, '__args__') and type_hint.__args__ is not None:
        new_args = []
        for arg in get_type_args(type_hint):
            new_args.append(
                replace_type_variable(type_, arg, type_var=type_var)
            )
        return type_hint.__origin__[tuple(new_args)]
    else:
        return type_hint


def get_type_and_value(value, symbol_table=None):
    if symbol_table is not None and isinstance(value, Identifier):
        value = symbol_table[value]

    if isinstance(value, Symbol):
        return value.type, value.value
    else:
        if isinstance(value, types.FunctionType):
            return typing_callable_from_annotated_function(value), value
        else:
            return type(value), value


def type_validation_value(value, type_, symbol_table=None):
    if type_ == typing.Any:
        return True

    if (
        (symbol_table is not None) and
        isinstance(value, Identifier)
    ):
        value = symbol_table[value].value
    elif isinstance(value, Symbol):
        print("Use symbol!")
        value = value.value

    if hasattr(type_, '__origin__'):
        if type_.__origin__ == typing.Union:
            return any(
                type_validation_value(value, t, symbol_table=symbol_table)
                for t in type_.__args__
            )
        elif issubclass(type_, typing.Callable):
            value_type, _ = get_type_and_value(value)
            return is_subtype(value_type, type_)
        elif issubclass(type_, typing.Mapping):
            return (
                issubclass(type(value), type_.__origin__) and
                ((type_.args is None) or all((
                    type_validation_value(
                        k, type_.__args__[0], symbol_table=symbol_table
                    ) and
                    type_validation_value(
                        v, type_.__args__[1], symbol_table=symbol_table
                    )
                    for k, v in value.items()
                )))
            )
        elif issubclass(type_, typing.Tuple):
            return (
                issubclass(type(value), type_.__origin__) and
                all((
                    type_validation_value(
                        v, t, symbol_table=symbol_table
                    )
                    for v, t in zip(value, type_.__args__)
                ))
            )
        elif any(
            issubclass(type_, t)
            for t in (typing.AbstractSet, typing.Sequence, typing.Iterable)
        ):
            return (
                issubclass(type(value), type_.__origin__) and
                ((type_.__args__ is None) or all((
                    type_validation_value(
                        i, type_.__args__[0], symbol_table=symbol_table
                    )
                    for i in value
                )))
            )
        else:
            raise ValueError("Type %s not implemented in the checker" % type_)
    else:
        return isinstance(
            value, type_
        )


class Symbol(object):
    def __init__(self, type_, value, symbol_table=None):
        if not type_validation_value(
            value, type_, symbol_table=symbol_table
        ):
            raise NeuroLangTypeException(
                "The value %s does not correspond to the type %s" %
                (value, type_)
            )
        self.type = type_
        self.value = value

    def __repr__(self):
        return '%s: %s' % (self.value, self.type)


class Identifier(object):
    def __init__(self, value):
        self.value = value

    def __getitem__(self, value):
        return Identifier(self.value + '.' + value)

    def parent(self):
        return Identifier(self.value[:self.value.rindex('.')])

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __repr__(self):
        return 'Id(%s)' % repr(self.value)


class SymbolTable(collections.MutableMapping):
    def __init__(self, enclosing_scope=None):
        self._symbols = collections.OrderedDict()
        self._symbols_by_type = collections.defaultdict(
            lambda: set()
        )
        self.enclosing_scope = enclosing_scope

    def __len__(self):
        return len(self._symbols)

    def __getitem__(self, key):
        try:
            return self._symbols[key]
        except KeyError:
            if self.enclosing_scope is not None:
                return self.enclosing_scope[key]
            else:
                raise KeyError("Symbol %s not in the table" % key)

    def __setitem__(self, key, value):
        if isinstance(value, Symbol):
            self._symbols[key] = value
            if value.type not in self._symbols_by_type:
                self._symbols_by_type[value.type] = dict()
            self._symbols_by_type[value.type][key] = value
        elif value is None:
            self._symbols[key] = None
        else:
            raise ValueError("Wrong assignment %s" % str(value))

    def __delitem__(self, key):
        value = self._symbols[key]
        del self._symbols_by_type[value.type][key]
        del self._symbols[key]

    def __iter__(self):
        keys = self._symbols.keys()
        act = self.enclosing_scope
        while act is not None:
            keys = act.keys() or keys
            act = act.enclosing_scope
        return iter(keys)

    def __repr__(self):
        return '{%s}' % (
            ', '.join([
                '%s: (%s)' % (k, v)
                for k, v in self._symbols.items()
            ])
        )

    def types(self):
        ret = self._symbols_by_type.keys()
        if self.enclosing_scope is not None:
            ret = ret or self._symbols_by_type.keys()
        return ret

    def symbols_by_type(self, type_):
        if self.enclosing_scope is not None:
            ret = self.enclosing_scope.symbols_by_type(type_)
        else:
            ret = dict()

        ret.update(self._symbols_by_type[type_])
        return ret

    def create_scope(self):
        subscope = SymbolTable(enclosing_scope=self)
        return subscope