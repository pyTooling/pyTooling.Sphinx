.. _ROLE/Breaks:

Line break and horizontal rule
##############################

.. grid:: 2

   .. grid-item::
      :columns: 6

      ``|br|`` is a line break, ``|hr|`` a horizontal rule - in HTML **and** in LaTeX. They are substitutions,
      appended to ``rst_prolog``, and delegate to the roles ``:br:`` and ``:hr:``. ``|degree|`` writes a degree sign.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         :param value: The first line. |br|
                       The second line.
