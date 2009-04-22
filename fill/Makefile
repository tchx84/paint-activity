#Copyright 2007, NATE-LSI-EPUSP

#Oficina is developed in Brazil at Escola Politécnica of 
#Universidade de São Paulo. NATE is part of LSI (Integrable
#Systems Laboratory) and stands for Learning, Work and Entertainment
#Research Group. Visit our web page: 
#www.nate.lsi.usp.br
#Suggestions, bugs and doubts, please email oficina@lsi.usp.br

#Oficina is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License 
#as published by the Free Software Foundation version 2 of 
#the License.

#Oficina is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.

#You should have received a copy of the GNU General Public
#License along with Oficina; if not, write to the
#Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, 
#Boston, MA  02110-1301  USA.
#The copy of the GNU General Public License is found in the 
#COPYING file included in the source distribution.


#Authors:

#Joyce Alessandra Saul               (joycealess@gmail.com)
#Andre Mossinato                     (andremossinato@gmail.com)
#Nathalia Sautchuk Patrício          (nathalia.sautchuk@gmail.com)
#Pedro Kayatt                        (pekayatt@gmail.com)
#Rafael Barbolo Lopes                (barbolo@gmail.com)
#Alexandre A. Gonçalves Martinazzo   (alexandremartinazzo@gmail.com)

CFLAGS = $(shell pkg-config --cflags gtk+-2.0 pygtk-2.0) \
		 $(shell python-config --cflags) \
		-fPIC

LDFLAGS = $(shell pkg-config --libs gtk+-2.0 pygtk-2.0) \
          $(shell python-config --libs)

ARCH = $(shell arch | grep 64 >/dev/null && echo linux64 || echo linux32)
PYTHON_VERSION = $(shell python -c 'import sys; print "%d%d" % sys.version_info[0:2]')
LIB_DIR = $(ARCH)_$(PYTHON_VERSION)

all: _fill.so
	rm -rf $(LIB_DIR)
	mkdir $(LIB_DIR)
	strip -s _fill.so
	mv _fill.so $(LIB_DIR)/
	touch $(LIB_DIR)/__init__.py

_fill.so: fill.o eggfill.o fillmodule.o
	$(LD) $(LDFLAGS) -shared $^ -o $@

DEFS=`pkg-config --variable=defsdir pygtk-2.0`
# Generate the C wrapper
fill.c: fill.defs fill.override
	pygtk-codegen-2.0 --prefix fill \
	--register $(DEFS)/gdk-types.defs \
	--register $(DEFS)/gdk-base.defs \
	--register $(DEFS)/gtk-types.defs \
	--override fill.override \
	fill.defs > $@

clean:
	rm -f *.so *.o fill.c *~ 

