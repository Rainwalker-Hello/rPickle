Quick Start
===========

.. code-block:: python

   import rPickle

   data = {"name": "Alice", "scores": [95, 87, 92]}
   packed = rPickle.dumps(data)
   restored = rPickle.loads(packed)

   print(restored)  # {'name': 'Alice', 'scores': [95, 87, 92]}