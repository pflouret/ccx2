from ccx2 import mifl
from pprint import pprint

s=' (or :performer :artist) > :album > (if :partofset (cat "CD" :partofset)) > :title'

p = mifl.MiflParser(s)
pprint(p)
