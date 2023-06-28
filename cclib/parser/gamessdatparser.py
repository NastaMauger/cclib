# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, the cclib development team
#
# This file is part of cclib (http://cclib.github.io) and is distributed under
# the terms of the BSD 3-Clause License.

"""Parser for GAMESS(US) .dat output files"""


import re
import numpy

from cclib.parser import logfileparser
from cclib.parser import utils

from cclib.parser.utils import PeriodicTable

class GAMESSDAT(logfileparser.Logfile):
    """A GAMESS .dat log file"""

    def __init__(self, *args, **kwargs):
        super().__init__(logname="GAMESSDAT", *args, **kwargs)

    def __str__(self):
        """Return a string representation of the object."""
        return f"GAMESS .dat log file {self.filename}"

    def __repr__(self):
        """Return a representation of the object."""
        return f'GAMESS .dat ("{self.filename}")'
    
    def normalisesym(self, label):
        """Normalise the symmetries used by GAMESS .dat."""

        pass

    def before_parsing(self):
        self.pt = PeriodicTable()
        # To change: declared only for passing unit tests

        self.mocoeffs = [ -1 ]
        self.metadata["input_file_contents"] = None
        self.metadata["legacy_package_version"] = None
        self.scfenergies = [ 0 ]
        self.b3lyp_energy = 0

    # def after_parsing(self):
    #     if hasattr(self, "atomcoords"):
    #         self.atomcoords = numpy.array(self.atomcoords)
        


    def extract(self, inputfile, line):
        """Extract information from the file object inputfile."""
        
        # Extract element and its properties

        # $DATA  
        # water                                                                           
        # C1       0
        # O           8.0      0.0000000000      0.0000000000      0.0000000000
        #    STO     3
                
        # H           1.0      0.9900000000      0.0000000000      0.0000000000
        #    STO     3
                
        # H           1.0     -0.2728810000      0.9516490000      0.0000000000
        #    STO     3
                
        #  $END   

        # Extract molecule name

        if line[1:6] == "$DATA":

            line = next(inputfile)
            name = line.split('\n')[0].strip()
            self.metadata["name"] = name

            # Extract atomic information

            self.atommasses = []
            # self.atomcoords = []

            line = next(inputfile)

            while line.strip() != "$END":
                parts = line.split()
                if len(parts) >= 2:

                    symbol      = parts[0]
                    mass        = float(parts[1])
                    coordinates = [float(coord) for coord in parts[2:]]

                    self.atommasses.append(mass)
                    # self.atomcoords.append(coordinates)
                    
                line = next(inputfile)


        # Extract energy

        # --- CLOSED SHELL ORBITALS --- GENERATED AT Mon Aug  5 13:05:47 2019
        # water                                                                           
        # E(RHF)=      -74.9643287920, E(NUC)=    8.8870072224,   13 ITERS

        # Extract E(RHF) value

        if "E(R" in line:
            val_pattern = r"E\(R[^,]+"
            match = re.search(val_pattern, line)
            val = float(match.group().split(' ')[-1])
            self.scfenergies = [ val ]

        # Extract E(NUC) value 

        if "E(NUC)=" in line:
            pattern_e_nuc = r"E\(NUC[^,]+"
            match_e_nuc = re.search(pattern_e_nuc, line)
            nuc_value = float(match_e_nuc.group().split(' ')[-1].strip())
            self.metadata["E_NUC"] = nuc_value

        # Extract number of ITERS 

        # if "ITERS" in line:
        #     iters_value = int(line.split()[-1])
        #     self.metadata["ITERS"] = iters_value

        
        # Extracting MP2 Energy Value

        # MP2 NATURAL ORBITALS, E(MP2)=      -75.0022821133
        
        if "E(MP2)=" in line:
            self.mpenergies = float(line.split()[-1])


        # Extracting Gaussian

        # ----- TOP OF INPUT FILE FOR BADER'S AIMPAC PROGRAM -----
        # water                                                                           
        # GAUSSIAN              7 MOL ORBITALS     21 PRIMITIVES        3 NUCLEI

        if line[0:8] == "GAUSSIAN":

            parts = line.split()

            self.nmo    = int(parts[1])
            self.nbasis = int(parts[4])
            self.natom  = int(parts[6])


            # Continue extracting
            
            #   O    1    (CENTRE  1)   0.00000000  0.00000000  0.00000000  CHARGE =  8.0
            #   H    2    (CENTRE  2)   1.87082873  0.00000000  0.00000000  CHARGE =  1.0
            #   H    3    (CENTRE  3)  -0.51567032  1.79835585  0.00000000  CHARGE =  1.0

            line = next(inputfile)

            atom_info = []
            self.atomcharges = dict()
            self.atomcharges['CHANGENAME'] = []
            self.atomnos = []
            
            while '(CENTRE' in line:

                parts = line.split()

                symbol = parts[0]
                atomno = self.pt.number[symbol]

                # atom_number = int(parts[1])
                # centre_number = int(parts[3][:-1])
                val1 = float(parts[4])
                val2 = float(parts[5])
                val3 = float(parts[6])

                charge = float(parts[-1])

                atom_info.append((val1, val2, val3))
                
                self.atomnos.append(atomno)
                self.atomcharges['CHANGENAME'].append(charge)

                line = next(inputfile)

            self.metadata['atom_info'] = atom_info


        # Extracting Centre Assignments

        # CENTRE ASSIGNMENTS    1  1  1  1  1  1  1  1  1  1  1  1  1  1  1  2  2  2  3  3
        # CENTRE ASSIGNMENTS    3
        
        self.atombasis = []

        while line[0:18] == "CENTRE ASSIGNMENTS":
            centre_assignments = re.findall(r'\d+', line)
            self.atombasis.extend(centre_assignments)
            line = next(inputfile)

        # Extracting Ttype Assignments

        # TYPE ASSIGNMENTS      1  1  1  1  1  1  2  2  2  3  3  3  4  4  4  1  1  1  1  1
        # TYPE ASSIGNMENTS      1

        self.metadata["type_assignments"] = []

        while line[0:16] == "TYPE ASSIGNMENTS":
            type_assignments = re.findall(r'\d+', line)
            self.metadata["type_assignments"].extend(type_assignments)
            line = next(inputfile)

        # Extracting Exponents

        # EXPONENTS  1.3070932E+02 2.3808866E+01 6.4436083E+00 5.0331513E+00 1.1695961E+00
        # EXPONENTS  3.8038896E-01 5.0331513E+00 1.1695961E+00 3.8038896E-01 5.0331513E+00
        # EXPONENTS  1.1695961E+00 3.8038896E-01 5.0331513E+00 1.1695961E+00 3.8038896E-01
        # EXPONENTS  3.4252509E+00 6.2391373E-01 1.6885540E-01 3.4252509E+00 6.2391373E-01
        # EXPONENTS  1.6885540E-01

        self.metadata["exponents"] = []
        
        while line[0:9] == 'EXPONENTS':
            exponents = re.findall(r"[-+]?(?:\d*\.*\d+)", line)
            self.metadata["exponents"].extend(exponents)
            line = next(inputfile)

        #   MO  1                     OCC NO =   2.00000000 ORB. ENERGY = -20.56547536
        #   8.27318851E-01  1.52270833E+00  2.46402951E+00  3.23903576E+00  2.77810215E+00
        #   9.49880307E-01 -1.29777421E-02 -5.79064323E-03  1.70998470E-02  2.67281545E-03
        #   2.05926021E-03  9.04126150E-04  3.54694672E-03  2.73273124E-03  1.19981620E-03
        #   0.00000000E+00  0.00000000E+00  0.00000000E+00  1.09508898E-03 -4.92215549E-05
        #  -6.53191563E-05  0.00000000E+00 -4.28769380E-03 -4.28529767E-03 -4.29025488E-03
        #   8.35523030E-06  0.00000000E+00  0.00000000E+00  3.26911333E-05  5.54503496E-05
        #   6.31282631E-05 -5.28069901E-05  4.95765497E-04 -8.70177406E-06  0.00000000E+00
        #   3.26910801E-05  5.54502594E-05  6.31281604E-05 -5.28070121E-05 -1.45016312E-04
        #   4.74162199E-04  0.00000000E+00
        # MO  2                     OCC NO =   2.00000000 ORB. ENERGY =  -1.32288835
        #  -1.75781895E-01 -3.23532524E-01 -5.23536695E-01 -6.88203640E-01 -5.90268263E-01
        #  -2.01822744E-01 -2.94878612E-01 -1.31574262E-01  3.88540558E-01  1.43700987E-01
        #   1.10713864E-01  4.86093496E-02  1.90697728E-01  1.46922319E-01  6.45068118E-02
        #   0.00000000E+00  0.00000000E+00  0.00000000E+00  1.16273118E-01  5.61500000E-03
        #   7.45135762E-03  0.00000000E+00  8.86485030E-03  9.17061568E-03  1.40727166E-03
        #   1.06632882E-03  0.00000000E+00  0.00000000E+00  2.90520499E-02  4.92777754E-02
        #   5.61010055E-02  2.64903112E-03 -3.82656636E-02  3.19859639E-03  0.00000000E+00
        #   2.90520559E-02  4.92777854E-02  5.61010170E-02  2.64903095E-03  1.36221368E-02
        #  -3.59016685E-02  0.00000000E+00
        # END DATA

        self.metadata["mocoeffs"] = []

        if line[0:3] == 'MO ':
            while 'END OF INPUT FILE FOR BADER' not in line:
                if 'MO' in line and 'OCC NO' in line and 'ORB. ENERGY' in line:
                    line = next(inputfile)
                    mo = []
                    while 'MO' not in line and 'END DATA' not in line:
                        mo.extend([float(x) for x in line.rsplit()])
                        line = next(inputfile)
                    self.metadata["mocoeffs"].append(mo)
                elif "VIRIAL(-V/T)" in line:
                    numbers = re.findall(r"[-+]?(?:\d*\.*\d+)", line)
                    self.metadata["energy"] = numbers[-2]
                    self.metadata["virial"] = numbers[-1]
                    line = next(inputfile)
                else:
                    line = next(inputfile)
        
                


