from .solver import SetBasedSolver, FiniteDomain, add_match
from .expressions import is_leq_informative, get_type_and_value, Expression, Predicate, Query
from typing import Set
from pprint import pprint
from io import StringIO


class Sulcus(FiniteDomain):
    def __init__(self, anterior, posterior, inferior, superior):
        self.anterior = anterior
        self.posterior = posterior
        self.inferior = inferior
        self.superior = superior

    def __getitem__(self, k: str)->Set['Sulcus']:
        if k in ('anterior', 'posterior', 'inferior', 'superior'):
            return getattr(self, k)

    def intersection(self, sulcus: 'Sulcus')->Set['Sulcus']:
        new_anterior = self.anterior.intersection(sulcus.anterior)
        new_posterior = self.posterior.intersection(sulcus.posterior)
        new_inferior = self.inferior.intersection(sulcus.inferior)
        new_superior = self.superior.intersection(sulcus.superior)

        return Sulcus(new_anterior, new_posterior, new_inferior, new_superior)

    def union(self, sulcus: 'Sulcus')->Set['Sulcus']:
        new_anterior = self.anterior.union(sulcus.anterior)
        new_posterior = self.posterior.union(sulcus.posterior)
        new_inferior = self.inferior.union(sulcus.inferior)
        new_superior = self.superior.union(sulcus.superior)

        return Sulcus(new_anterior, new_posterior, new_inferior, new_superior)

    def difference(self, sulcus: 'Sulcus')->Set['Sulcus']:
        new_anterior = self.anterior.difference(sulcus.anterior)
        new_posterior = self.posterior.difference(sulcus.posterior)
        new_inferior = self.inferior.difference(sulcus.inferior)
        new_superior = self.superior.difference(sulcus.superior)

        return Sulcus(new_anterior, new_posterior, new_inferior, new_superior)

    def __and__(self, sulcus: 'Sulcus')->Set['Sulcus']:
        return self.intersection(sulcus)

    def __or__(self, sulcus: 'Sulcus')->Set['Sulcus']:
        return self.union(sulcus)

    def __sub__(self, sulcus: 'Sulcus')->Set['Sulcus']:
        return self.difference(sulcus)

    def __repr__(self):
        strio = StringIO()
        for a in ('anterior', 'posterior', 'inferior', 'superior'):
            strio.write(a + ": ")
            pprint(getattr(self, a), stream=strio)
        return(strio.getvalue())


class SulcusSolver(SetBasedSolver):
    type = Sulcus
    type_name = "sulcus"
    plural_type_name = "sulci"

    @add_match(Query[Sulcus])
    def predicate(self, expression):
        argument_type, argument = get_type_and_value(
            expression,
            symbol_table=self.symbol_table
        )

        if ast['identifier'].name in (
            "anterior_to", "posterior_to", "superior_to", "inferior_to"
        ):
            predicate = ast['identifier'].name[:-3]
            if not is_leq_informative(argument_type, self.type):
                raise ValueError()
            return Expression(
                argument[predicate],
                type_=Set[self.type],
                symbol_table=self.symbol_table
            )
        if ast['identifier'].name == 'with_limb':
            if not is_leq_informative(argument_type, self.type):
                raise
            return argument
        else:
            return super().predicate(ast)