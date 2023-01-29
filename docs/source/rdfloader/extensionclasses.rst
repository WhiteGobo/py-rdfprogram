extension classes
~~~~~~~~~~~~~~~~~

The :py:class:`rdfloader.classloader.constructor_annotation` is used as annotation for.

example implementation of a loadable class
..........................................

To tell how the algrithm of :py:func:`rdfloader.load_from_graph` can load
the information in the form of pythonclasses, you have to tell how it can 
convert the resources given in the knowledge graph
into attributes for the constructor. Every Annotation must be an subclass
(or feasible as) :py:class:`rdfloader.classloader.constructor_annotation`.

Here a little example, how a class (in the example :py:class:`loadable_class`)
can be written, so the algorithm :py:func:`rdfloader.load_from_graph`
can work with it.

The given callable method, must start with an attribute for the IRI. This IRI
can depending on the knowledgegraph also be a 
:py:class:`blank node identifier<rdflib.BNode>`.
Every other attribte of the callable must be annotated, so that the algorithm
knows, which resource should be loaded and then given to tha callable.
Generally the resources will be identified over the triple (uri to self, property, target resource), The target resource will be identified over the
property which is specified in the annotation.

Things the annotation will specify for the callable:
        
        * how target resources will be found and given to the callable.
        * is the resource optional or required.
        * Is the target resource required at the generationtime or can
          it be set after the generation through 
          setattr( obj, attr, objects according to annotation )
        * in which form will the target resources be given to the callable.
          Eg it can be given as sngle obj (obj1) or as list ([obj1, obj2])
          and even as dict ({property-object: object-object, ...})

See the :py:class:`rdfloader.classloader.constructor_annotation` for 
detailed information. See :py:module:`rdfloader.extension_classes` for
a complete list of all implemented extension classes.


.. code:: python

    from rdfloader import extension_classes as extc
    class loadable_class( base ):
        def __init__(self, uri, val: extc.info_attr(prop, needed=True)):
            self.uri = uri
            if val is not None:
                self.val = val
                if not isinstance( self.val, (base, int, str, float) ):
                    raise TypeError( self.val )

Additionally the :py:class:`rdfloader.classloader.constructor_annotation`
defines the method :py:meth:`find_objects<rdfloader.classloader.constructor_annotation.find_objects>`.
The implementation of this method defines, how the algorithm identifies the needed resources.

