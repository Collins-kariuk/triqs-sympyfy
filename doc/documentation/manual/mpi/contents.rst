triqs/MPI
=========


Introduction
------------

The purpose of the MPi library is to provide a simplified, C++-style API to the MPI routines for standard types
(those for which an MPI type exists) and for composite higher-level objects, in particular the TRIQS arrays and Green's functions.

The communication routines in the C API of the MPI library have require several parameters, such as the ``reduce`` operation:

.. code-block:: cpp

  int MPI_Reduce(void *sendbuf, void *recvbuf, int count,
                 MPI_Datatype datatype, MPI_Op op, int root, MPI_Comm comm)

In principle, all parameters except for the communicator and id of the root process can be determined from the variable or object to be transmitted.
In most cases, we use ``MPI_COMM_WORLD`` as the communicator, take the id 0 for the root process and use ``MPI_SUM`` as the operation.

This allows us to write

.. code-block:: c

  int a = 5;
  mpi::reduce(a);

Such an interface is simpler to use and much less error prone. For higher-level objects, such as vectors or higher-dimensional arrays, the simplifcation is even more significant. Take the scatter and gather operations as examples:

.. code-block:: c

  int MPI_Scatter(void *sendbuf, int sendcount, MPI_Datatype sendtype,
                  void *recvbuf, int recvcount, MPI_Datatype recvtype, int root,
                  MPI_Comm comm)

.. code-block:: c

  int MPI_Gather(void *sendbuf, int sendcount, MPI_Datatype sendtype,
                 void *recvbuf, int recvcount, MPI_Datatype recvtype, int root,
                 MPI_Comm comm)

In order to scatter a (contiguos) multidimensional array across all nodes, apply some operations to it and gather it back on the master one requires several lines of relatively complex code.
The leading dimension of the array needs to be sliced, slice length and adress of the first element of each slice have to be computed and finally the MPI C API function has to be called.
This can be packaged in the library once and for all.

Using the library these operations look as follows:

.. code-block:: c

 nda::array<int, 3> A(8, 8, 8); // a three-dimensional array
 mpi::scatter(A);
 //do something with the corresponding part of A on each node
 mpi::gather(A);

All index computations are encapsulated in the mpi library calls.

In this library, we employ metaprogramming techniques for type deduction as well as a lazy mechanism to avoid unecessary copyies of data.


MPI documentation/manual/triqs
------------------------------

In this document, we describe the use of the TRIQS MPI library. For more information on MPI, see, e.g., the `open MPI web pages <http://www.open-mpi.org>`_ or consult the MPI documentation/manual/triqs documentation/manual.


Supported functions and types
-----------------------------

Currently, the TRIQS MPI library supports the following operations::

  reduce
  allreduce
  broadcast
  scatter
  gather
  allgather

These routines have the same meaning as their corresponding MPI analogues.
They work for all 'basic' types, i.e. types for which a native MPI-type exists. These are::

  int
  long
  unsigned long
  double
  float
  std::complex<double>

We also support ``std::vector<T>`` for ``T`` being a basic type, as well as the types provided by the TRIQS ``array`` and TRIQS ``gf`` libraries.
In addition, the library provides a mechanism to enable MPI support for custom containers based on the array or gf libraries.


Basic usage
-----------

In order to create an MPI environment, set up the communicator and broadcast a variable, use the following code block:

.. code-block:: c

  int main(int argc, char* argv[]) {

    mpi::environment env(argc, argv);
    mpi::communicator world;

    int a = 5;
    broadcast(a, world);

  }

The declaration of the communicator is optional. If no communicator is passed to the routine, ``MPI_COMM_WORLD`` is used by default.

All collective operations have the same signature. They take up to three arguments:

.. code-block:: c

  reduce(T const &x, communicator = {}, int root = 0)

Here T can be any supported type. The communicator is optional. By default, the data will be collected on (or transmitted from) the process with id 0.


Headers
-------

Support for built-in types is provided by the header ``mpi/mpi.hpp``, while string, pair and vector have their own headers ``mpi/string.hpp``, ``mpi/pair.hpp`` and ``mpi/vector.hpp``.
Support for array types is provided by ``nda/mpi.hpp``.


MPI example
-----------

.. literalinclude:: /documentation/manual/triqs/mpi/mpi_0.cpp
   :language: cpp

.. literalinclude:: /documentation/manual/triqs/mpi/mpi_0.output

Simple MPI example.
