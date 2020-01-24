# -*- coding: utf-8 -*-

import base64
import os
import subprocess
import logging
# import requests
# import json


class CheckDigit(object):

    # Definicion modulo 11
    _MODULO_11 = {
        'BASE': 11,
        'FACTOR': 2,
        'RETORNO11': 0,
        'RETORNO10': 1,
        'PESO': 2,
        'MAX_WEIGHT': 7
    }

    # noinspection PyMethodParameters
    @classmethod
    def _eval_mod11(self, modulo):
        if modulo == self._MODULO_11['BASE']:
            return self._MODULO_11['RETORNO11']
        elif modulo == self._MODULO_11['BASE'] - 1:
            return self._MODULO_11['RETORNO10']
        else:
            return modulo

    # noinspection PyMethodParameters
    @classmethod
    def compute_mod11(self, dato):
        """
        Calculo mod 11
        return int
        """
        total = 0
        weight = self._MODULO_11['PESO']

        for item in reversed(dato):
            total += int(item) * weight
            weight += 1
            if weight > self._MODULO_11['MAX_WEIGHT']:
                weight = self._MODULO_11['PESO']
        mod = 11 - total % self._MODULO_11['BASE']

        mod = self._eval_mod11(mod)
        return mod


class Xades(object):

    # noinspection PyMethodMayBeStatic
    def sign(self, xml_document, file_pk12, password):
        """
        Metodo que aplica la firma digital al XML
        TODO: Revisar return
        """
        # xml_str = xml_document.encode('utf-8')
        xml_str = xml_document
        JAR_PATH = 'firma/firmaXadesBes10.jar'
        JAVA_CMD = 'java'
        firma_path = os.path.join(os.path.dirname(__file__), JAR_PATH)

        # noinspection PyUnusedLocal
        data = {'java_cmd': JAVA_CMD,
                'jar': '-jar',
                'firma_path': firma_path,
                'xml_str': xml_str,
                'file_pk': base64.b64encode(file_pk12.encode()).decode('ascii'),
                'pass_pk': base64.b64encode(password.encode()).decode('ascii')}

        # a = requests.post('http://localhost:9006/xades/api/v1.0/ec_sign', json=data)
        # a = a.json()
        # print(a.json())
        # return a['file_str']
        command = [
            JAVA_CMD, "-XX:CompressedClassSpaceSize=10m",
            '-jar',
            firma_path,
            xml_str,
            base64.b64encode(file_pk12.encode()).decode('ascii'),
            base64.b64encode(password.encode()).decode('ascii')
        ]
        try:
            subprocess.check_output(command)
        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            output = e.output
            logging.error('Llamada a proceso JAVA codigo: %s' % returncode)
            logging.error('Error: %s' % output)

        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        res = p.communicate()
        return res[0]
