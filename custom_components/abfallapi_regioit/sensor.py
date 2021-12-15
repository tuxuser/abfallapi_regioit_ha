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
CONF_ORT = 'ort'
CONF_STRASSE = 'strasse'

_QUERY_SCHEME = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ANBIETER_ID): cv.string,
    vol.Required(CONF_ORT): cv.string,
    vol.Required(CONF_STRASSE): cv.string,
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
                                     config.get(CONF_ORT),
                                     config.get(CONF_STRASSE),
                                     value_template)])

class RegioItAbfallSensor(Entity):

    """Representation of a Sensor."""
    def __init__(self, name, base_url, ort, strasse, value_template):
        """Initialize the sensor."""
        self._name = name

        self._ort = ort
        self._strasse = strasse

        self._api = RegioItAbfallApi(base_url)

        self._value_template = value_template
        self._state = STATE_UNKNOWN
        self._attributes = None

        self.update()

    def strip_multiple_whitespaces(self, input_str):
        return ' '.join(input_str.split())

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
    def extra_state_attributes(self):
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
        Get Orte
        """
        try:
            with self._api.get_orte() as url:
                orte = json.loads(url.read().decode())
        except Exception as e:
            _LOGGER.error('API call error: Orte, error: {}'.format(e))
            return

        valid_orte = [o for o in orte if self.strip_multiple_whitespaces(o['name']) == self._ort]

        if not valid_orte:
            _LOGGER.error('No ort with name {0} was found!'.format(self._ort))
            return
        elif len(valid_orte) > 1:
            _LOGGER.error('More than one match for ort {0} was found! Matches: {1}'.format(self._ort, valid_orte))
            return
        else:
            ort_id = valid_orte[0]['id']

        """
        Get Streets
        """
        try:
            with self._api.get_strassen_all(ort_id) as url:
                streets = json.loads(url.read().decode())
        except Exception as e:
            _LOGGER.error('API call error: Strassen All, error: {}'.format(e))
            return

        valid_streets = [s for s in streets if self.strip_multiple_whitespaces(s['name']) == self._strasse]

        if not valid_streets:
            _LOGGER.error('No street with name {0} was found!'.format(self._strasse))
            return
        elif len(valid_streets) > 1:
            _LOGGER.error('More than one match for street \'{0}\' was found! Matches: {1}'.format(self._strasse, valid_streets))
            return
        else:
            strassen_id = valid_streets[0]['id']

        """
        Get Termine
        """
        try:
            with self._api.get_termine(strassen_id) as url:
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

