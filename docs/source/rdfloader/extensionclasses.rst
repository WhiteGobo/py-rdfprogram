extension classes
~~~~~~~~~~~~~~~~~

The :py:class:`rdfloader.classloader.constructor_annotation` is used as annotation for.

example implementation of a loadable class
..........................................

To tell how the algorithm of :py:func:`rdfloader.load_from_graph` can load
the information in the form of pythonclasses, you have to tell how it can 
convert the resources given in the knowledge graph
into attributes for the constructor. Every Annotation must be an subclass
(or feasible as) :py:class:`rdfloader.extension_classes.constructor_annotation`.

Here a little example, how a class (in the example :py:class:`loadable_class`)
can be written, so the algorithm :py:func:`rdfloader.load_from_graph`
can work with it.

.. code:: python

        import rdflib
        from rdfloader import extension_classes as extc
        prop = rdflib.URIRef("http://example.com#myproperty")
        class loadable_class( base ):
                def __init__(self, uri, val: extc.info_attr(prop)):
                        (...)

The given callable method, must start with an attribute for the IRI. This IRI
can depending on the knowledgegraph also be a 
:py:class:`blank node identifier<rdflib.BNode>`.
Every other attribute (here val) must be annotated, so that the algorithm
knows, which resources are used as input.
Generally the target resources will be identified over the triple 
(uri, prop, target resource). How different annotation objects find
the target resources, see :py:func:`constructor_annotation.find_objects<rdfloader.extension_classes.constructor_annotation.find_objects>`.

Things the annotation will specify for the callable:
        
        * how target resources will be found and given to the callable.
        * is the resource optional or required.
        * Is the target resource required at the generationtime or can
          it be set after the generation through 
          setattr( obj, attr, objects according to annotation )
        * in which form will the target resources be given to the callable.
          Eg it can be given as sngle obj (obj1) or as list ([obj1, obj2])
          and even as dict ({property-object: object-object, ...})

See the :py:class:`rdfloader.extension_classes.constructor_annotation` for 
detailed information. See :py:module:`rdfloader.extension_classes` for
a complete list of all implemented extension classes.

implement type control for __init__ or for property
...................................................

Because for each IRI multiple resources can be generated it's necessary to 
implement a type control, when the parameter is given to the constructor
or set as attribute for the created object.

Here are 2 examples for a type control:

.. code:: python

    from rdfloader import extension_classes as extc
    class loadable_class( base ):
        def __init__(self, uri, val: extc.info_attr(prop, needed=True)):
            self.uri = uri
            if val is not None:
                self.val = val
                if not isinstance( self.val, (int, float) ):
                    raise TypeError( self.val )


.. code:: python

    from rdfloader import extension_classes as extc
    class loadable_class( base ):
        def __init__(self, uri, val: extc.info_attr(prop, needed=True)):
                self.uri = uri
                self.val = val

        def _set_val(self, val):
                attr_list = ["attr1", "attr2"]
                if not all(hasattr(val, attr) for attr in attr_list ):
                        raise TypeError(val, "cant be used here")
                self._val = val
        def _get_val(self, val):
                try:
                        return self._val
                except AttributeError:
                        return None
        val = property(fget=_get_val, fset=_set_val)
