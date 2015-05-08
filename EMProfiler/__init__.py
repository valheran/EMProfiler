# -*- coding: utf-8 -*-
"""
/***************************************************************************
 EMProfiler
                                 A QGIS plugin
 Makes channel profiles for EM lines
                             -------------------
        begin                : 2015-05-08
        copyright            : (C) 2015 by Alex Brown
        email                : sdgdg
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load EMProfiler class from file EMProfiler.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .EMProfiler import EMProfiler
    return EMProfiler(iface)
