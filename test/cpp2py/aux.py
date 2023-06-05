# Copyright (c) 2014 Commissariat à l'énergie atomique et aux énergies alternatives (CEA)
# Copyright (c) 2014 Centre national de la recherche scientifique (CNRS)
# Copyright (c) 2020 Simons Foundation
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
# Authors: Olivier Parcollet, Nils Wentzell


def ffg( *args, **kw) : 
    """ my doc of ffg in module """
    print("calling ffg, with :")
    print(args)
    print(kw)
    #return [2*x for x in args], kw
    return tuple(2*x for x in args), kw


def post1(res) : 
    return [res]


def pure_py1(self, i) : 
    """ 
      doc of pure_py1 : a nice funciton ,...
    """
    i = i/2
    print(" I am in pure python method pure_py1 %s "%i)
    return ["pure_py1 return list"]
