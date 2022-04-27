from functools import wraps
from typing import Optional, Any, Callable, Tuple, Type

import numpy as np
from rpy2.rinterface import Sexp
from rpy2.robjects import default_converter, numpy2ri, baseenv
from rpy2.robjects import Vector, BoolVector, IntVector, FloatVector
from rpy2.robjects.conversion import localconverter
from rpy2.robjects.packages import Package
from scipy import sparse

from ..rpy2_ext import importr
from .conv import converter


methods: Optional[Package] = None
as_logical: Optional[Callable[[Any], BoolVector]] = None
as_integer: Optional[Callable[[Any], IntVector]] = None
as_double: Optional[Callable[[Any], FloatVector]] = None


def get_type_conv(dtype: np.dtype) -> Tuple[str, Callable[[np.ndarray], Sexp], Type[Vector]]:
    if np.issubdtype(dtype, np.floating):
        return "d", as_double, FloatVector
    elif np.issubdtype(dtype, np.bool_):
        return "l", as_logical, BoolVector
    else:
        raise ValueError(f"Unknown dtype {dtype!r} cannot be converted to ?gRMatrix.")

#
# def py2r_context(f):
#     @wraps(f)
#     def wrapper(obj):
#         global methods, as_logical, as_integer, as_double
#         if methods is None:
#             importr("Matrix")  # make class available
#             methods = importr("methods")
#             as_logical = baseenv["as.logical"]
#             as_integer = baseenv["as.integer"]
#             as_double = baseenv["as.double"]
#
#         with localconverter(default_converter + numpy2ri.converter):
#             return f(obj)
#
#     return wrapper

def _py2r(x):
    import rpy2.robjects as ro
    with localconverter(
        default_converter
        + numpy2ri.converter
    ):
        x = ro.conversion.py2rpy(x)
    return x


def py2r_context(f):
    @wraps(f)
    def wrapper(obj):
        global methods, as_logical, as_integer, as_double
        if methods is None:
            print('Running the if methods block')
            importr("Matrix")  # make class available
            methods = importr("methods")
            as_logical = lambda x:baseenv["as.logical"](_py2r(x))
            as_integer = lambda x:baseenv["as.integer"](_py2r(x))
            as_double = lambda x:baseenv["as.double"](_py2r(x))

        return f(obj)

    return wrapper



from rpy2.rinterface import FloatSexpVector, IntSexpVector
from rpy2.robjects.vectors import IntVector, FloatVector
@converter.py2rpy.register(sparse.csc_matrix)
@py2r_context
def csc_to_rmat(csc: sparse.csc_matrix):
    csc.sort_indices()
    t, conv_data, _ = get_type_conv(csc.dtype)

    # print('hallo')
    # if False:
    #     # as_integer = baseenv["as.integer"]
    #     as_integer = IntVector
    #     conv_data = FloatVector
    #     print('as_integer', as_integer)
    # else:
    #     as_logical = lambda x:baseenv["as.logical"](_py2r(x))
    #     as_integer = lambda x:baseenv["as.integer"](_py2r(x))
    #     as_double = lambda x:baseenv["as.double"](_py2r(x))

    i = as_integer(csc.indices.tolist())
    p=as_integer(csc.indptr.tolist())
    # x=conv_data(csc.data.tolist())
    x=as_double(csc.data.tolist())
    Dim=as_integer(list(csc.shape))


    print('t', type(t), t )
    print('i',type(i), i )
    print('p',type(p), p )
    print('x',type(x), x )
    print('Dim',type(Dim), Dim )

    return methods.new(
        f"{t}gCMatrix",
        i=i,
        p=p,
        x=x,
        Dim=Dim,
    )


@converter.py2rpy.register(sparse.csr_matrix)
@py2r_context
def csr_to_rmat(csr: sparse.csr_matrix):
    csr.sort_indices()
    t, conv_data, _ = get_type_conv(csr.dtype)
    return methods.new(
        f"{t}gRMatrix",
        j=as_integer(csr.indices),
        p=as_integer(csr.indptr),
        x=conv_data(csr.data),
        Dim=as_integer(list(csr.shape)),
    )


@converter.py2rpy.register(sparse.coo_matrix)
@py2r_context
def coo_to_rmat(coo: sparse.coo_matrix):
    t, conv_data, _ = get_type_conv(coo.dtype)
    return methods.new(
        f"{t}gTMatrix",
        i=as_integer(coo.row),
        j=as_integer(coo.col),
        x=conv_data(coo.data),
        Dim=as_integer(list(coo.shape)),
    )


@converter.py2rpy.register(sparse.dia_matrix)
@py2r_context
def dia_to_rmat(dia: sparse.dia_matrix):
    t, conv_data, vec_cls = get_type_conv(dia.dtype)
    if len(dia.offsets) > 1:
        raise ValueError(
            "Cannot convert a dia_matrix with more than 1 diagonal to a *diMatrix. "
            f"R diagonal matrices only support 1 diagonal, but this has {len(dia.offsets)}."
        )
    is_unit = np.all(dia.data == 1)
    return methods.new(
        f"{t}diMatrix",
        x=vec_cls([]) if is_unit else conv_data(dia.data),
        diag="U" if is_unit else "N",
        Dim=as_integer(list(dia.shape)),
    )
