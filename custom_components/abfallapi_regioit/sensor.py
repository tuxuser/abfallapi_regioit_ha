#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
AWB GL App:
https://play.google.com/store/apps/details?id=de.regioit.abfallapp.awbgl&hl=de
"""

import logging
from homeassistant.const import (
    CONF_NAME,
    CONF_VALUE_TEMPLATE,
    STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
import voluptuous as vol
import urllib.request
import json
from datetime import datetime
from datetime import timedelta

from .regioit_abfall_api import RegioItAbfallApi, CITIES

_LOGGER = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%d'

CONF_ANBIETER_ID = 'anbieter_id'
CONF_ORT_ID = 'ort_id'
CONF_STRASSEN_ID = 'strassen_id'

_QUERY_SCHEME = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ANBIETER_ID): cv.string,
    vol.Required(CONF_ORT_ID): cv.string,
    vol.Required(CONF_STRASSEN_ID): cv.string,
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template
})

def setup_platform(
    hass,
    config,
    add_devices,
    discovery_info=None
    ):
    """Setup the sensor platform."""
    value_template = config.get(CONF_VALUE_TEMPLATE)
    if value_template is not None:
        value_template.hass = hass

    anbieter_id = config.get(CONF_ANBIETER_ID)
    base_url = CITIES[anbieter_id]

    add_devices([RegioItAbfallSensor(config.get(CONF_NAME),
                                     base_url,
                                     config.get(CONF_ORT_ID),
                                     config.get(CONF_STRASSEN_ID),
                                     value_template)])

class RegioItAbfallSensor(Entity):

    """Representation of a Sensor."""
    def __init__(self, name, base_url, ort_id, strassen_id, value_template):
        """Initialize the sensor."""
        self._name = name

        self._ort_id = ort_id
        self._strassen_id = strassen_id

        self._api = RegioItAbfallApi(base_url)

        self._value_template = value_template
        self._state = STATE_UNKNOWN
        self._attributes = None

        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        tommorow = datetime.now() + timedelta(days=1)

        """
        Get Müllarten
        """
        try:
            with self._api.get_fraktionen() as url:
                fraktionen = json.loads(url.read().decode())
        except Exception as e:
            _LOGGER.error('API call error: Fraktionen, error: {}'.format(e))
            return
        
        fraktionen = {entry['id']:entry for entry in fraktionen}

        """
        Get Termine
        """
        try:
            with self._api.get_termine(self._strassen_id) as url:
                termine = json.loads(url.read().decode())
        except Exception as e:
            _LOGGER.error('API call error: Termine, error: {}'.format(e))
            return
        
        """
        Sort Termine by date
        """
        tmp_termine = dict()
        for entry in termine:
            datum = entry['datum']
            del entry['datum']

            if datum not in tmp_termine:
                tmp_termine[datum] = list()
            
            tmp_termine[datum].append(entry)
        
        termine = tmp_termine
        
        attributes = {}
        for date, abfuhren in sorted(termine.items()):
            muell = None
            for abfuhr in abfuhren: 
                fraktion_id = abfuhr['bezirk']['fraktionId']
                muell_typ = fraktionen.get(fraktion_id).get('name')
                muell = muell_typ if not muell else ', '.join([muell, muell_typ])
    
            attributes.update({date: muell})
        
        attributes.update({'Zuletzt aktualisiert': datetime.now().strftime(DATE_FORMAT + ' %H:%M:%S')})
        data = attributes.get(tommorow.strftime(DATE_FORMAT), "Keine")

        if self._value_template is not None:
            self._state = self._value_template.async_render_with_possible_json_value(
                data, None)
        else:
            self._state = data

        self._attributes = dict(sorted(attributes.items()))
