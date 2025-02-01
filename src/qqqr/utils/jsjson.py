import ast
import logging
from textwrap import dedent
from typing import Dict, List, Union

logger = logging.getLogger(__name__)
BaseTypes = Union[int, float, bool, str]
JsonDict = Dict[BaseTypes, "JsonValue"]
JsonList = List["JsonValue"]
JsonValue = Union[BaseTypes, JsonDict, JsonList]


class AstLoader:
    """:class:`AstLoader` uses standard :mod:`ast` module to parse the js/json"""

    class RewriteUndef(ast.NodeTransformer):
        """
        :meta private:
        """

        const = {
            "undefined": ast.Constant(value=None),
            "null": ast.Constant(value=None),
            "true": ast.Constant(value=True),
            "false": ast.Constant(value=False),
        }

        def visit_Name(self, node: ast.Name):
            if node.id in self.const:
                return self.const[node.id]
            return ast.Constant(value=node.id)

    @classmethod
    def json_loads(cls, js: str, filename: str = "stdin") -> JsonValue:
        """
        The :meth:`~AstLoader.json_loads` function loads a JSON object from a js/json string. It uses standard
        :mod:`ast` module to parse the js/json.

        :param js: Used to Pass the js/json string to be parsed.
        :param filename: Used to Specify the name of the file that is being read. This is only for debug use.
        :return: A :obj:`JsonValue` object.
        """
        js = dedent(js).replace(r"\/", "/")
        node = ast.parse(js, mode="eval")
        node = ast.fix_missing_locations(cls.RewriteUndef().visit(node))
        code = compile(node, filename, mode="eval")
        return eval(code)


def json_loads(js: str) -> JsonValue:
    """The :meth:`json_loads` function converts a string representation of JS/JSON data into a Python object.
    Current implementation is using :external+python:mod:`ast`.

    .. seealso:: :meth:`.AstLoader.json_loads`

    If you need more parameters or another implementation, call ``xxxLoader.json_loads`` instead.

    :param js: Used to Pass the JS/JSON string.
    :return: A :obj:`JsonValue` object.
    """
    return AstLoader.json_loads(js)
