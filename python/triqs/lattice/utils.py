# Copyright (c) 2021-2022 Simons Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You may obtain a copy of the License at
#     https:#www.gnu.org/licenses/gpl-3.0.txt
#
# Authors: Michel Ferrero, Alexander Hampel, Nils Wentzell, phibeck

from io import StringIO
import numpy as np
from itertools import product as itp
import warnings

__all__ = ['k_space_path', 'TB_from_wannier90']


def k_space_path(paths, num=101, bz=None):
    """ Generate an array of k-vectors along a path defined by a list of pairs of k-vectors

    Parameters
    ----------
    paths : list of pairs of three-vectors of floats
       List of pairs of k-vectors (in reciprocal units) to create a path in-between.
    num : int, default=100
       Number of k-vectors along each segment the paths
    bz : brillouin_zone, optional
       When a Brillouin Zone is passed, calculate distance in absolute units

    Returns
    -------
    kvecs: numpy.array [shape=(len(paths)*num,3)]
        Two-dimensional numpy array containing the path vectors (in reciprocal units) as rows
    dist: numpy.array  [shape=(kvecs.shape[0])]
        One-dimensional numpy array containing, for each element in kvecs,
        the distance travelled along the path. Useful for plotting.
        If bz is provided, calculate the distance in absolute units.
        The distances for the relevant k-points in paths can be obtained with dist[num-1::num].
    """

    if bz is None:
        cell = np.eye(3)
    else:
        cell = bz.units

    x = np.linspace(0., 1., num=num)
    kvecs = [ki[None, :] + x[:, None] * (kf - ki)[None, :] for ki, kf in paths]

    cur_dist = 0.0
    dist = np.array([], dtype=float)
    for kvec in kvecs:
        kvec_abs = np.dot(kvec, cell)
        dist_new = np.linalg.norm(kvec_abs - kvec_abs[0], axis=1) + cur_dist
        dist = np.concatenate((dist, dist_new))

        cur_dist = dist[-1]

    return np.vstack(kvecs), dist


# ----------------------------------------------------------------------
def parse_hopping_from_wannier90_hr_dat(filename):
    r""" Wannier90 real space hopping parser of ``*_hr.dat`` files.

    Returns a dictionary where the keys are the real-space hopping vectors,
    in terms of multiples of the lattice vectors, and the values are
    ``num_wann * num_wann`` numpy ndarrays with the hopping integrals.

    Parameters
    ----------
    filename : str
        Wannier90 ``*_hr.dat`` file to parse.

    Returns
    -------
    hopp_dict : dict
        Dictionary of real space hoppings.
    num_wann : int
        Total number of Wannier functions per unit-cell.

    """

    with open(filename, 'r') as fd:
        fd.readline()  # eliminate time header
        num_wann = int(fd.readline())
        nrpts = int(fd.readline())
        lines = fd.readlines()

    # Read R Vector degeneracies, At most 15 elements before line-break
    nlines = int(np.ceil(nrpts / 15.))
    deg = np.array("".join(lines[:nlines]).split(), dtype=int)
    assert deg.shape == (nrpts,)

    # Read R Vector and Hopping data
    dat = "".join(lines[nlines:])
    dat = np.loadtxt(StringIO(dat))
    dat = dat.reshape(nrpts, num_wann, num_wann, 7)
    R = dat[:, 0, 0, 0:3].astype(int)
    hopp = dat[..., 5] + 1.j * dat[..., 6]

    # Account for degeneracy of the Wigner-Seitz points
    hopp /= deg[:, None, None]

    # Dict with hopping matrices
    hopp_dict = {tuple(R[i]): hopp[i] for i in range(nrpts)}

    return hopp_dict, num_wann


def parse_lattice_vectors_from_wannier90_wout(filename):
    r""" Wannier90 real space lattice vectors parser of ``*.wout`` files.

    Parameters
    ----------
    filename : str
        Wannier90 ``*.wout`` file to parse.

    Returns
    -------
    vectors : list of three three-tuples of floats
        Lattice vectors.

    """

    with open(filename, 'r') as fd:
        lines = fd.readlines()

    # -- Find start of data in text file
    for idx, line in enumerate(lines):
        if 'Lattice Vectors' in line:
            if '(Ang)' in line:
                unit = 1.0
            elif '(Bohr)' in line:
                unit = 0.5291772105638411
            else:
                raise NotImplementedError
            break

    if 'Lattice Vectors' not in line:
        raise IOError

    # Read vector data and scale by unit length
    lines = "".join(lines[idx+1:idx+4])
    dat = np.loadtxt(StringIO(lines), usecols=(1, 2, 3))
    dat *= unit

    # Convert 3x3 data to list of tuples
    vectors = [tuple(dat[i]) for i in range(3)]

    return vectors


def extend_wannier90_to_spin(hopp_dict, num_wann):
    hopp_dict_spin = {k: np.kron(np.eye(2), v) for k, v in hopp_dict.items()}
    return hopp_dict_spin, 2 * num_wann


def TB_from_wannier90(seed, path='./',  extend_to_spin=False, add_local=None):
    r"""
    read wannier90 output and convert to TBLattice object

    reads wannier90 real space lattice vectors from seed.wout file.
    reads wannier90 hoppings from seed_hr.dat file

    Parameters
    ----------
    seed : str
        seedname of wannier90 run, name of *_hr.dat
    path : str, default = './'
        path to wannier90 output dir
    extend_to_spin: bool, default= False
        extend hopping Hamiltonian with spin indices
    add_local: numpy array , default = None
        add a local term to hopping[0,0,0] of shape Norb x Norb

    Returns
    -------
    TBL : triqs TBLattice object
        triqs tight binding object

    """

    from triqs.lattice.tight_binding import TBLattice

    hopp_dict, num_wann = parse_hopping_from_wannier90_hr_dat(path + seed + '_hr.dat')
    units = parse_lattice_vectors_from_wannier90_wout(path + seed + '.wout')

    if extend_to_spin:
        hopp_dict, num_wann = extend_wannier90_to_spin(hopp_dict, num_wann)

    if add_local is not None:
        hopp_dict[(0, 0, 0)] += add_local

    # Should we use hopp_dict or hopping?
    TBL = TBLattice(units=units, hoppings=hopp_dict,
                    orbital_positions=[(0, 0, 0)]*num_wann,
                    orbital_names=[str(i) for i in range(num_wann)])
    return TBL

def TB_from_pythTB(ptb):
    r"""
    convert pythTB model to TBLattice object

    Parameters
    ----------
    ptb : pythtb.tb_model
        pythTB tight-binding object

    Returns
    -------
    TBL : triqs TBLattice object
        triqs tight binding object

    """

    from triqs.lattice.tight_binding import TBLattice

    # initialize objects
    hopp_dict = {}
    m_zero = np.zeros((ptb.get_num_orbitals(), ptb.get_num_orbitals()), dtype=complex)

    # fill on-site energies
    hopp_dict[(0, 0, 0)] = np.eye(ptb.get_num_orbitals(), dtype=complex) * ptb._site_energies

    # fill hoppings
    for hopp, orb_from, orb_to, displacement in ptb._hoppings:
        if tuple(displacement) not in hopp_dict:
            hopp_dict[tuple(displacement)] = m_zero.copy()
            # per default pythTB does not explicitly stores -R
            hopp_dict[tuple(-np.array(displacement))] = m_zero.copy()

        hopp_dict[tuple(displacement)][orb_from, orb_to] += hopp
        # fill -R from +R using H_ij(+R)=[H_ji(-R)]*
        # if the user specified -R explicitly we have to sum both hopping matrices
        # according to pythTB documentation
        hopp_dict[tuple(-np.array(displacement))][orb_to, orb_from] += np.conj(hopp)

    TBL = TBLattice(units=ptb.get_lat(), hopping=hopp_dict,
                    orbital_positions=ptb.get_orb(),
                    orbital_names=[str(i) for i in range(ptb.get_num_orbitals())])

    return TBL


def sympyfy(tb_lat_obj, analytical = True, precision = 6):
    r"""
    returns the analytical form of the momentum space hamiltonian of the tight-binding model 
    from a tight-binding lattice object, by utilizing Fourier series
    
    Parameters
    ----------
    tb_lat_obj: triqs TBLattice object
        triqs tight binding object
    analytical: boolean, default = True
        a boolean which will cause the function will return an analytical Hamiltonian, when true, and 
        an numerical Hamiltonian otherwise
    precision: integer, default = 6
        An integer that specifies the decimal point precision of the floating point hopping amplitudes of
        the electrons involved in the hoppings
        Wannier90's default precision is 10^-6 which is why the default precision is 6
        The user might want to decrease the default precision to ensure that similar hopping amplitudes
        especially those tied to symmetrical hoppings across the crysal lattice are easily recognizable
    
    Returns
    -------
    Hk: NumPy array
        The hamiltonian of the tight-binding model in momentum space. This can be returned either in
        numerical form (Hk_numerical) or reduced analytical form (Hk) depending the user's preference.
        The default output, which depends on the optional analytical parameter, is the reduced analytical form
        The numerical form only depends on the k-space vector components, i.e., the lattice constants and
        lattice vectors are expressed numerically
        The analytical form depends on the k-space vector components alongside the lattice vectors too

    """

    import sympy as sp

    # imaginary number
    I = sp.I

    # matrix from the axis directions in momentum space
    kx, ky, kz = sp.symbols("kx ky kz", real = True)
    k_space_matrix = sp.Matrix([kx, ky, kz])

    # symbolic dot product representation between the lattice unit vectors
    # and the momentum space matrix
    a1k, a2k, a3k = sp.symbols("a1k a2k a3k", real = True)
    lattice = sp.Matrix([a1k, a2k, a3k])

    # the number of orbitals involved in the electron hoppings
    num_orb = tb_lat_obj.n_orbitals

    # dictionary containing details about the hopping of the electrons
    TB_lat_obj_hops = tb_lat_obj.hoppings 

    # maximum hopping distances of electrons in each of the axial directions
    max_x, max_y, max_z = list(np.max(np.array(list(TB_lat_obj_hops.keys())), axis = 0))

    # number of cells involved in the hopping of electrons in each of the axial directions
    num_cells_x, num_cells_y, num_cells_z = [2 * max_coord + 1 for max_coord in [max_x, max_y, max_z]]
    
    # basis of the 5D tensor real-space Hamiltonian
    Hrij = np.zeros((num_cells_x, num_cells_y, num_cells_z, num_orb, num_orb), dtype = sp.exp)

    # looping through the hopping parameters of the electrons involved in the inter-orbital hoppings
    # key represents the cell coordinates of where the electrons hop to relative to the home unit cell
    # hopping represents the matrix with the embedded hopping amplitudes
    for key, hopping in TB_lat_obj_hops.items():
        rx, ry, rz = key
        # reduce floating point precision of hopping parameters to 3 decimal places
        hopping = np.around(hopping, precision)
        Hrij[rx + max_x, ry + max_y, rz + max_z] = hopping

    # basis of the exponential term in the calculation of Hk
    Hexp = np.empty_like(Hrij, dtype = sp.exp)

    # perform the Fourier transform
    for xi, yi, zi in itp(range(num_cells_x), range(num_cells_y), range(num_cells_z)):
        coefficients = np.array([xi - max_x, yi - max_y, zi - max_z])
        r = lattice.dot(coefficients)
        eikr = sp.exp(-I * r)
        Hexp[xi, yi, zi, :, :] = eikr

    # summation over all real space axes
    Hk = np.sum(Hrij * Hexp, axis = (0, 1, 2))
    
    # rewriting the exponential terms in the analytical expression in terms of 
    for i, j in itp(range(num_orb), repeat = 2):
        Hk[i, j] = Hk[i, j].rewrite(sp.cos)

    # dealing with the numerical Hamiltonian
    # we convert it to a SymPy matrix to use the substitutions method available in SymPy
    Hk_numerical = sp.Matrix(Hk)
    TB_lat_obj_units = tb_lat_obj.units
    TB_lat_obj_units_transpose = np.transpose(TB_lat_obj_units)
    
    # obtaining unit vectors
    # reduce floating point precision to 3 decimal places
    a1 = np.around(TB_lat_obj_units_transpose[0], precision)
    a2 = np.around(TB_lat_obj_units_transpose[1], precision)
    a3 = np.around(TB_lat_obj_units_transpose[2], precision)

    # numerical dot products between the unit vectors
    # and the momentum space matrix
    a1k_numerical = a1.dot(k_space_matrix)[0]
    a2k_numerical = a2.dot(k_space_matrix)[0]
    a3k_numerical = a3.dot(k_space_matrix)[0]
    
    # performing the numerical dot product substitutions
    Hk_numerical = Hk_numerical.subs(a1k, a1k_numerical)
    Hk_numerical = Hk_numerical.subs(a2k, a2k_numerical)
    Hk_numerical = Hk_numerical.subs(a3k, a3k_numerical)

    # converting the numerical Hamiltonian to a NumPy array from a SymPy matrix
    Hk_numerical = np.array(Hk_numerical)

    def _has_complex_exponential_sympy(matrix):
        """
        Checks if a NumPy array containing SymPy elements has a complex exponential element.

        Args:
            matrix (NumPy array): The input NumPy array containing SymPy elements
        
        Returns:
            bool: True if the matrix array contains a complex exponential element, False otherwise.
        
        """
        
        for sublist in matrix:
            for element in sublist:
                if element.is_complex and element.has(sp.exp):
                    return True
        return False
    
    def _is_hermitian_sympy(matrix):
        """
        Checks if a NumPy array containing SymPy elements is hermitian

        Args:
            matrix (NumPy array): The input NumPy array containing SymPy elements
        
        Returns:
            bool: True if the matrix is a hermitian, False otherwise

        """

        n = matrix.shape[0]
        for i in range(n):
            for j in range(n):
                if matrix[i, j] != matrix[j, i].conjugate():
                    return False
        return True
    
    # warning indicating when the output Hamiltonian is not hermitian
    if _is_hermitian_sympy(Hk) == False or _is_hermitian_sympy(Hk_numerical) == False:
        return warnings.warn("The resulting Hamiltonian is not hermitian.")

    # warning indicating when the Hamiltonian contains a complex exponential element
    if _has_complex_exponential_sympy(Hk_numerical) or _has_complex_exponential_sympy(Hk):
        return warnings.warn("""Your expression has a complex exponential. 
                                Choosing a different unit cell could make 
                                your Hamiltonian expression real.""")
    
    # returning the analytical or numerical form of the Hamiltonian
    # depending on the user's preference
    if analytical:
        return Hk
    return Hk_numerical
