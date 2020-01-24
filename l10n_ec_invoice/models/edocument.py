# -*- coding: utf-8 -*-

# ---------------------------
# Notes:    LIBRERIAS PYTHON
# ---------------------------

# noinspection PyUnresolvedReferences
from odoo import api, fields, models

# noinspection PyUnresolvedReferences
from odoo.exceptions import (ValidationError, Warning as UserError)

from ..xades.sri import DocumentXML

from io import StringIO
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from xml.etree import cElementTree as ET

import xmlrpc.client as xmlrpclib
import base64
import logging
import pytz
import itertools
import os
import re


# ----------------------------------------------------------------------------------------------------------------------
# OOOOO O     OOOOO OOOOO OOOOO OOOOO OOOOO O   O OOO OOOOO   OOOO  OOOOO OOOOO O   O O   O OOOOO O   O OOOOO OOOOO
# O     O     O     O       O   O   O O   O OO  O  O  O       O   O O   O O     O   O OO OO O     OO  O   O   O
# OOO   O     OOO   O       O   OOOOO O   O O O O  O  O       O   O O   O O     O   O O O O OOO   O O O   O   OOOOO
# O     O     O     O       O   O  O  O   O O  OO  O  O       O   O O   O O     O   O O   O O     O  OO   O       O
# OOOOO OOOOO OOOOO OOOOO   O   O   O OOOOO O   O OOO OOOOO   OOOO  OOOOO OOOOO OOOOO O   O OOOOO O   O   O   OOOOO
# ----------------------------------------------------------------------------------------------------------------------
# ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
#   O   OOOOO OOOOO OOOOO O   O O   O OOOOO     OOO  O   O O   O OOOOO  OOO  OOOOO OOOOO
#  O O  O     O     O   O O   O OO  O   O        O   OO  O O   O O   O   O   O     O
# O   O O     O     O   O O   O O O O   O        O   O O O O   O O   O   O   O     OOO
# OOOOO O     O     O   O O   O O  OO   O        O   O  OO  O O  O   O   O   O     O
# O   O OOOOO OOOOO OOOOO OOOOO O   O   O       OOO  O   O   O   OOOOO  OOO  OOOOO OOOOO
# ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # ---------------------
    # DEFINICION DE CAMPOS
    # ---------------------
    estado = fields.Selection(
        [
            ('01', 'RIDE & XML PENDIENTES'),
            ('02', 'SRI VALIDACION PENDIENTE'),
            ('03', 'SRI AUTORIZACION PENDIENTE'),
            ('04', 'SRI AUTORIZADO'),
            ('00', 'ERROR')
        ],
        string='Estado SRI',
        readonly=True,
        required=True,
        default='01',
        copy=False,
        help='Estado de los comprobantes electrónicos'
    )
    # ---------------------
    # DEFINICION DE CAMPOS
    # ---------------------
    estado_lc = fields.Selection(
        [
            ('01', 'RIDE & XML PENDIENTES'),
            ('02', 'SRI VALIDACION PENDIENTE'),
            ('03', 'SRI AUTORIZACION PENDIENTE'),
            ('04', 'SRI AUTORIZADO'),
            ('00', 'ERROR')
        ],
        string='LC Estado SRI',
        readonly=True,
        default='01',
        required=True,
        copy=False,
        help='Estado de los comprobantes electrónicos'
    )
    bool_on_off_estado = fields.Boolean(
        string='Cambio de estado',
        default=False,
        copy=False,
        help='MARQUE PARA MODIFICAR EL ESTADO DEL DOCUMENTO'
    )
    bool_on_off_estado_lc = fields.Boolean(
        string='LC Cambio de estado',
        default=False,
        copy=False,
        help='MARQUE PARA MODIFICAR EL ESTADO DEL DOCUMENTO'
    )
    historial = fields.Text(
        string='Historial SRI',
        copy=False
    )

    adjuntos = {}

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def validar_xml(self, tipo_comprobante_descripcion):

        inv_xml = {}

        # --------------------------------------------------------------------------------------------------------------
        # INICIA EL PROCESO DE VALIDACION DE COMPROBANTES ELECTRONICOS EN EL SRI
        # -----------------------------------------------------------------------
        try:
            if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                log_msg = 'ODOO: %s' % 'LIQUIDACION DE COMPRA' + ' No: ' + self.doc_electronico_no_lc
                logging.info(log_msg)
                self.history_log(log_msg)

                log_msg = 'ODOO: CLAVE DE ACCESO: ' + self.doc_electronico_no_autorizacion_lc
                logging.info(log_msg)
                self.history_log(log_msg)
            else:
                log_msg = 'ODOO: %s' % self.doc_electronico_tipo + ' No: ' + self.doc_electronico_no
                logging.info(log_msg)
                self.history_log(log_msg)

                log_msg = 'ODOO: CLAVE DE ACCESO: ' + self.doc_electronico_no_autorizacion
                logging.info(log_msg)
                self.history_log(log_msg)

            if self.estado == '01' or self.estado == '02' or self.estado == '03':  # PENDIENTE, AUTORIZADO o EN PROCESO
                # ------------------------------------------------------------------------------------------------------
                # ODOO: LECTURA DEL ARCHIVO XML archivo_basico Y CORRECCION DE CARCATERES
                # ESPECIALES DE ESTE ARCHIVO EN archivo_basico_fix_xml
                # ------------------------------------------------------------------
                try:
                    ruta_archivo_xml = self.company_id.company_ruta_documentos
                    if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                        nombre_archivo_xml = ruta_archivo_xml + self.doc_electronico_xml_lc
                    else:
                        nombre_archivo_xml = ruta_archivo_xml + self.doc_electronico_xml
                    # nombre_archivo_xml = ruta_archivo_xml + self.doc_electronico_xml + 'R'
                    # ----------------------------------------------------------------------
                    # RECUPERA DEL DISCO EL ARCHIVO XML EN FORMATO TEXTO archivo_basico_xml
                    # ----------------------------------------------------------------------
                    archivo_basico = open(nombre_archivo_xml, "r", encoding='utf8')
                    archivo_basico_xml = archivo_basico.read()
                    log_msg = 'ODOO: LECTURA DE ARCHIVO XML - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)
                    # ----------------------------------------------------------------------
                    # CAMBIA LOS CARACTERES ESPECIALES Y CREA archivo_basico_fix_xml
                    # ----------------------------------------------------------------------
                    archivo_basico_fix_xml = self.replace_fix_chars(archivo_basico_xml)

                except Exception as error_message:
                    # ------------------------------------------------------------------
                    # ERROR DE LECTURA Y DE CAMBIO DE CARACTERES DEL archivo_basico_xml
                    # ------------------------------------------------------------------
                    log_msg = 'ODOO: LECTURA DE ARCHIVO XML - ' + str(error_message).replace("'", "").upper()
                    logging.info(log_msg)

                    raise UserError(str(log_msg))

                # ------------------------------------------------------------------------------------------------------
                # SRI: CARGA EL ESQUEMA PARA EL TIPO DE DOCUMENTO ELECTRONICO Y
                # VALIDA EL ARCHIVO archivo_basico_fix_xml EN EL FORMATO XML
                # --------------------------------------------------------------
                try:
                    # -------------------------------------------------
                    # DEFINE inv_xml EN FUNCION DEL ESQUEMA ESPECIFICO
                    # -------------------------------------------------
                    if self.tipo_documento_tributario == 'DOCUMENTO DE COMPRA':
                        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                            inv_xml = DocumentXML(archivo_basico_fix_xml, 'purchase_clearance')
                        else:
                            inv_xml = DocumentXML(archivo_basico_fix_xml, 'withdrawing')
                    if self.tipo_documento_tributario == 'FACTURA DE VENTA':
                        inv_xml = DocumentXML(archivo_basico_fix_xml, 'out_invoice')
                    if self.tipo_documento_tributario == 'NOTA DE CREDITO DE VENTA':
                        inv_xml = DocumentXML(archivo_basico_fix_xml, 'out_refund')
                    if self.tipo_documento_tributario == 'GUIA DE REMISION':
                        inv_xml = DocumentXML(archivo_basico_fix_xml, 'delivery')
                    # -----------------------------------------------------------
                    # VALIDA EL ARCHIVO archivo_basico_fix_xml EN EL FORMATO XML
                    # -----------------------------------------------------------
                    validador, mensaje_autorizacion = inv_xml.validate_xml()
                    # validador, mensaje_autorizacion = False, 'ERROR 00 ERROR DE VALIDACION SIMULADO'
                    # -------------------------------------------------------------------
                    # ERROR DE LECTURA DE ESQUEMA Y VALIDACION ETREE DEL ARCHIVO XML FIX
                    # -------------------------------------------------------------------
                    if not validador:
                        raise UserError(str(mensaje_autorizacion))

                    log_msg = 'ODOO: VALIDADOR LOCAL DE LA ESTRUCTURA XML - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                except Exception as error_message:
                    log_msg = 'ODOO: VALIDADOR LOCAL DE LA ESTURCTURA XML - ' + str(error_message).replace("'", "")
                    logging.info(log_msg)

                    raise UserError(str(log_msg))

        except Exception as error_message:
            # ------------------------------------------------------------------------------------
            # ERROR DENTRO DE ESTE PROCESO DETIENE LA VALIDACION DEL FORMULARIO DE ODOO
            # ------------------------------------------------------------------------------------
            log_msg = 'ERROR: FIRMA ELECTRONICA - ' + str(error_message). \
                replace("'", ""). \
                replace("(", ""). \
                replace(")", ""). \
                replace(",", ""). \
                upper()

            logging.info(log_msg)

            log_msg = log_msg + '\n\nCONTACTE A SU ASESOR DE ODOO'

            # -------------------------------------------------------------
            # TERMINA EL PROCESO DE FIRMA ELECTRONICA CON MENSAJE DE ERROR
            # -------------------------------------------------------------
            raise UserError(str(log_msg))

        return inv_xml

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def firma_electronica(self, tipo_comprobante_descripcion):

        inv_xml = {}
        archivo_firmado_xml = ''
        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
            doc_electronico_tipo = 'LIQUIDACION DE COMPRA'
            doc_electronico_no = self.doc_electronico_no_lc
            doc_electronico_no_autorizacion = self.doc_electronico_no_autorizacion_lc
            doc_electronico_xml = self.doc_electronico_xml_lc
            # ------------------------------------------------------
            # UNLINK ELIMINA todos los archivos si existiere alguno
            # ------------------------------------------------------
            ADJUNTOS_IDS = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion_lc)])
            for adjuntos_ids in ADJUNTOS_IDS:
                adjuntos_ids.unlink()
            # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion_lc)])
            ADJUNTOS_IDS = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
            for adjuntos_ids in ADJUNTOS_IDS:
                adjuntos_ids.unlink()
            # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
        else:
            doc_electronico_tipo = self.doc_electronico_tipo
            doc_electronico_no = self.doc_electronico_no
            doc_electronico_no_autorizacion = self.doc_electronico_no_autorizacion
            doc_electronico_xml = self.doc_electronico_xml
            # ------------------------------------------------------
            # UNLINK ELIMINA todos los archivos si existiere alguno
            # ------------------------------------------------------
            ADJUNTOS_IDS = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
            for adjuntos_ids in ADJUNTOS_IDS:
                adjuntos_ids.unlink()

            # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])

        # --------------------------------------------------------------------------------------------------------------
        # INICIA EL PROCESO DE VALIDACION DE COMPROBANTES ELECTRONICOS EN EL SRI
        # -----------------------------------------------------------------------
        try:
            log_msg = 'ODOO: %s' % doc_electronico_tipo + ' No: ' + doc_electronico_no
            logging.info(log_msg)
            self.history_log(log_msg)

            log_msg = 'ODOO: CLAVE DE ACCESO: ' + doc_electronico_no_autorizacion
            logging.info(log_msg)
            self.history_log(log_msg)

            if self.estado == '01' or self.estado == '02' or self.estado == '03':  # PENDIENTE, AUTORIZADO o EN PROCESO
                # ------------------------------------------------------------------------------------------------------
                # ODOO: LECTURA DEL ARCHIVO XML archivo_basico Y CORRECCION DE CARCATERES
                # ESPECIALES DE ESTE ARCHIVO EN archivo_basico_fix_xml
                # ------------------------------------------------------------------
                try:
                    ruta_archivo_xml = self.company_id.company_ruta_documentos
                    nombre_archivo_xml = ruta_archivo_xml + doc_electronico_xml
                    # nombre_archivo_xml = ruta_archivo_xml + self.doc_electronico_xml + 'R'
                    # ----------------------------------------------------------------------
                    # RECUPERA DEL DISCO EL ARCHIVO XML EN FORMATO TEXTO archivo_basico_xml
                    # ----------------------------------------------------------------------
                    archivo_basico = open(nombre_archivo_xml, "r", encoding='utf8')
                    archivo_basico_xml = archivo_basico.read()
                    log_msg = 'ODOO: LECTURA DE ARCHIVO XML - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)
                    # ----------------------------------------------------------------------
                    # CAMBIA LOS CARACTERES ESPECIALES Y CREA archivo_basico_fix_xml
                    # ----------------------------------------------------------------------
                    archivo_basico_fix_xml = self.replace_fix_chars(archivo_basico_xml)

                except Exception as error_message:
                    # ------------------------------------------------------------------
                    # ERROR DE LECTURA Y DE CAMBIO DE CARACTERES DEL archivo_basico_xml
                    # ------------------------------------------------------------------
                    log_msg = 'ODOO: LECTURA DE ARCHIVO XML - ' + str(error_message).replace("'", "").upper()
                    logging.info(log_msg)

                    raise UserError(str(log_msg))

                # ------------------------------------------------------------------------------------------------------
                # SRI: CARGA EL ESQUEMA PARA EL TIPO DE DOCUMENTO ELECTRONICO Y
                # VALIDA EL ARCHIVO archivo_basico_fix_xml EN EL FORMATO XML
                # --------------------------------------------------------------
                try:
                    # -------------------------------------------------
                    # DEFINE inv_xml EN FUNCION DEL ESQUEMA ESPECIFICO
                    # -------------------------------------------------
                    if self.tipo_documento_tributario == 'DOCUMENTO DE COMPRA':
                        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                            inv_xml = DocumentXML(archivo_basico_fix_xml, 'purchase_clearance')
                        else:
                            inv_xml = DocumentXML(archivo_basico_fix_xml, 'withdrawing')
                    if self.tipo_documento_tributario == 'FACTURA DE VENTA':
                        inv_xml = DocumentXML(archivo_basico_fix_xml, 'out_invoice')
                    if self.tipo_documento_tributario == 'NOTA DE CREDITO DE VENTA':
                        inv_xml = DocumentXML(archivo_basico_fix_xml, 'out_refund')
                    if self.tipo_documento_tributario == 'GUIA DE REMISION':
                        inv_xml = DocumentXML(archivo_basico_fix_xml, 'delivery')
                    # -----------------------------------------------------------
                    # VALIDA EL ARCHIVO archivo_basico_fix_xml EN EL FORMATO XML
                    # -----------------------------------------------------------
                    validador, mensaje_autorizacion = inv_xml.validate_xml()
                    # validador, mensaje_autorizacion = False, 'ERROR 00 ERROR DE VALIDACION SIMULADO'
                    # -------------------------------------------------------------------
                    # ERROR DE LECTURA DE ESQUEMA Y VALIDACION ETREE DEL ARCHIVO XML FIX
                    # -------------------------------------------------------------------
                    if not validador:
                        raise UserError(str(mensaje_autorizacion))

                    log_msg = 'ODOO: VALIDADOR LOCAL DE LA ESTRUCTURA XML - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                except Exception as error_message:
                    log_msg = 'ODOO: VALIDADOR LOCAL DE LA ESTRUCTURA XML - ' + str(error_message).replace("'", "")
                    logging.info(log_msg)

                    raise UserError(str(log_msg))

                # ------------------------------------------------------------------------------------------------------
                # XADES: AÑADE LA FIRMA ELECTRONICA AL ARCHIVO XML
                # ------------------------------------------
                try:
                    # -------------------------------------------------
                    # XMLRPC: GENERA LOS ARGUMENTOS DE LA API
                    # -------------------------------------------------
                    password = self.company_id.password_electronic_signature

                    # -------------------------------------------------
                    # XADES LOCAL: FIRMA ELECTRONICA DEL DOCUMENTO
                    # -------------------------------------------------
                    # xades = Xades()
                    # archivo_pk12 = self.company_id.electronic_signature
                    # password = self.company_id.password_electronic_signature
                    # archivo_firmado_xml = xades.sign(archivo_basico_fix_xml, archivo_pk12, password)
                    # archivo_firmado_xml = archivo_firmado_xml.decode('ascii')

                    # ----------------------------------------------------
                    # CONEXION DE SERVICIOS WEB XMLRPC
                    # SE CONECETA CON LA BASE DE DATOS sri CREADA EN ODDO
                    # Y UBICADA EN UN SERVIDOR EXTERNO
                    # ----------------------------------------------------
                    host_port = self.company_id.ip_ruc
                    db = 'sri'
                    user = self.env['res.users'].search([('id', '=', 2)]).login
                    pwd = self.env['res.partner'].search([('id', '=', 1)]).vat
                    srv = 'http://%s' % host_port
                    # -------------------------------------------------
                    # XMLRPC: VERIFICA CONECCION Y AUTENTIFICA
                    # -------------------------------------------------
                    common = xmlrpclib.ServerProxy('%s/xmlrpc/common' % srv)  # VERIFICACION
                    server_version = common.version()['server_version']
                    # user = 'otro'
                    # pwd = 'otro'
                    uid = common.authenticate(db, user, pwd, {})  # AUTENTIFICACION
                    if not uid:
                        # -------------------------------------------------
                        # ERROR EN XADES: USURIO NO REGISTRADO EN BASE sri
                        # -------------------------------------------------
                        log_msg = 'ODOO: USUARIO O CLAVE DE USUARIO NO REGISTRADOS AL SERVIDOR DE FIRMA ELECTRONICA'
                        logging.info(log_msg)

                        raise UserError(str(log_msg))

                    log_msg = 'ODOO: CONECTANDO CON SERVIDOR: ' + srv + ' ODOO Version: ' + server_version + ' USUARIO REGISTRADO id: ' + str(uid)
                    logging.info(log_msg)
                    # --------------------------------------------------------
                    # XADES REMOTO: FIRMA ELECTRONICA
                    # XMLRPC: ACTIVA LA Application Programming Interface API
                    # --------------------------------------------------------
                    api = xmlrpclib.ServerProxy('%s/xmlrpc/object' % srv)

                    archivo_firmado_xml = api.execute_kw(db, uid, pwd, 'sri.ruc', 'firma_electronica', [[]],
                                                         {
                                                             'archivo_basico_fix_xml': archivo_basico_fix_xml,
                                                             'password': password,
                                                             'user_id': uid
                                                         }
                                                         )
                    # -------------------------------------------------
                    # ERROR EN XADES: FIRMA ELECTRONICA DEL DOCUMENTO
                    # -------------------------------------------------
                    if "No se puede generar KeyStore" in archivo_firmado_xml:
                        message = 'XADES: ' + archivo_firmado_xml.split("\n")[0] + " / " + archivo_firmado_xml.split("\n")[1]
                        log_msg = str(message).replace("'", "").upper()
                        logging.info(log_msg)

                        raise UserError(str(log_msg))

                    log_msg = 'XADES: FIRMA ELECTRONICA DEL DOCUMENTO - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                except Exception as error_message:
                    # -------------------------------------------------
                    # ERROR EN XADES: FIRMA ELECTRONICA DEL DOCUMENTO
                    # -------------------------------------------------
                    log_msg = 'XADES: ' + str(error_message).replace("'", "").upper()
                    logging.info(log_msg)

                    raise UserError(str(log_msg))

                # ------------------------------------------------------------------------------------------------------
                # GENERACION DE ARCHIVOS ADJUNTOS RIDE & XML SIN FECHA DE AUTORIZACION
                # ---------------------------------------------------------------------
                try:

                    # adjuntos_ids = self.add_attachment(autorizacion_xml)[0]

                    self.add_attachment_xml(archivo_firmado_xml)[0]
                    self.add_attachment_pdf(archivo_firmado_xml)[0]

                    log_msg = 'ODOO: CREACION DE ARCHIVOS ADJUNTOS RIDE & XML - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                except Exception as error_message:
                    # -------------------------------------------------
                    # ERROR EN GENERACION DE ARCHIVOS ADJUNTOS
                    # -------------------------------------------------
                    log_msg = 'ODOO: ADVERTENCIA - CREACION DE ARCHIVOS RIDE & XML - ' + str(error_message).replace("'", "")
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                        self.estado_lc = "01"  # RIDE & XML PENDIENTES
                    else:
                        self.estado = "01"  # RIDE & XML PENDIENTES

                    return

                # ------------------------------------------------------------------------------------------------------
                # ODOO: ENVIO DE CORREO ELECTRONICO CON ADJUNTOS RIDE & XML
                # ----------------------------------------------------------
                try:
                    if self.partner_id.email:
                        adjuntos_ids = self.env['ir.attachment'].search(
                            [('name', 'like', doc_electronico_no_autorizacion)])
                        self.send_document(
                            attachments=[a.ids for a in adjuntos_ids],
                            template='l10n_ec_invoice.email_template_invoice'
                        )
                        log_msg = 'ODOO: CORREO ELECTRONICO ENVIADO A: ' + self.partner_id.email + ' - (Ok)'
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                            self.estado_lc = "02"  # SRI VALIDACION PENDIENTE
                        else:
                            self.estado = "02"  # SRI VALIDACION PENDIENTE

                    else:
                        log_msg = 'ODOO: NO SE ENVIO EL CORREO A ' + self.partner_id.name + '. RECEPTOR SIN DIRECCION'
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                            self.estado_lc = "02"  # SRI VALIDACION PENDIENTE
                        else:
                            self.estado = "02"  # SRI VALIDACION PENDIENTE

                    # ------------------------------------------------------
                    # SE ELIMINA LOS PDFs EN EXCESO QUE GENERA EL SISTEMA
                    # ------------------------------------------------------
                    # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
                    if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                        # ------------------------------------------------------
                        # UNLINK ELIMINA EL PDF EN EXCESO QUE GENERA EL SISTEMA
                        # ------------------------------------------------------
                        adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
                        adjuntos_ids.unlink()
                        # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
                        adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion_lc)])
                        adjuntos_ids[1].unlink()
                        # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion_lc)])
                    else:
                        # ------------------------------------------------------
                        # UNLINK ELIMINA EL PDF EN EXCESO QUE GENERA EL SISTEMA
                        # ------------------------------------------------------
                        adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
                        adjuntos_ids[1].unlink()
                        # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])

                    # adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])

                except Exception as error_message:
                    # ----------------------------------------------------------
                    # WARNING EN ENVIO DE CORREO CON ARCHIVOS ADJUNTOS RIDE Y XML
                    # ----------------------------------------------------------
                    log_msg = 'ODOO: ADVERTENCIA - ENVIO DE CORREO ELECTRONICO - ' + str(error_message).replace("'", "").upper()
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                        self.estado_lc = "01"  # RIDE & XML PENDIENTES
                    else:
                        self.estado = "01"  # RIDE & XML PENDIENTES

                    return

        except Exception as error_message:
            # ------------------------------------------------------------------------------------
            # ERROR DENTRO DE ESTE PROCESO DETIENE LA VALIDACION DEL FORMULARIO DE ODOO
            # ------------------------------------------------------------------------------------
            log_msg = 'ERROR: FIRMA ELECTRONICA - ' + str(error_message).\
                replace("'", "").\
                replace("(", "").\
                replace(")", "").\
                replace(",", "").\
                upper()

            logging.info(log_msg)

            log_msg = log_msg + '\n\nCONTACTE A SU ASESOR DE ODOO'

            # -------------------------------------------------------------
            # TERMINA EL PROCESO DE FIRMA ELECTRONICA CON MENSAJE DE ERROR
            # -------------------------------------------------------------
            raise UserError(str(log_msg))

        return inv_xml, archivo_firmado_xml

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def validar_comprobante_sri(self, inv_xml, archivo_firmado_xml, tipo_comprobante_descripcion):
        # ------------------------------------------------------------------------------------------------------
        # SRI: VALIDAR COMPROBANTE - CONEXION, ENVIO DEL XML
        # -----------------------------
        try:
            if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                estado = self.estado_lc
            else:
                estado = self.estado

            if estado == "02":
                # ----------------------------------------------------------------------------
                # DETERMINA EL TIPO DE CONECCION CON EL SRI (PRUEBAS/PRODUCCION/ON O OFFLINE)
                # ----------------------------------------------------------------------------
                # noinspection PyProtectedMember
                url_recepcion, url_autorizacion = self.company_id._get_ws()
                # --------------------------
                # ENVIA EL DOCUMENTO AL SRI
                # --------------------------
                validador_recepcion, errores, codigo_error, respuesta_sri = inv_xml.send_receipt(
                    archivo_firmado_xml, url_recepcion)

                if not validador_recepcion:
                    # --------------------------------------------------------------------------------------------------------
                    # SI validador_recepcion == False --> EL SRI EMITIÓ UN ERROR EN LA VALIDACION DEL COMPROBANTE ELECTRONICO
                    # --------------------------------------------------------------------------------------------------------
                    # if codigo_error != '70' and codigo_error != '43':
                    if int(codigo_error) in [26, 28, 35, 36, 45, 47, 48, 49, 50, 65, 67]:
                        # -----------------------------------------------------------------------------------
                        # CODIGOS DE ERRORES DE WS validarComprobante QUE DETIENEN EL PROCESO DE FACTURACION
                        # ESTOS DOCUMENTOS DEBEN REVISARSE Y ANULARSE EN EL SISTEMA. PUEDE QUE REQUIERAN
                        # REVISION EN LA CODIFICACION
                        # -----------------------------------------------------------------------------------
                        log_msg = 'ERROR: VALIDAR COMPROBANTE: ' + str(errores).replace("'", "").upper()
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        raise UserError(str(log_msg))

                    if int(codigo_error) in [34, 42, 52, 64, 65, 69]:
                        # -----------------------------------------------------------------------------------
                        # CODIGOS DE ERRORES DE WS validarComprobante QUE DETIENEN EL PROCESO DE FACTURACION
                        # ESTOS ERRORES DEBEN SER PARTE DEL SISTEMA CONTABLE PARA EVITAR LA GENERACION Y
                        # ENVIO DE COMPROBANTES AL SRI POR PARTE DE LOS DESARROLLADORES
                        # -----------------------------------------------------------------------------------
                        log_msg = 'ERROR: VALIDAR COMPROBANTE: NO CUMPLE REQUISITOS: ' + \
                                  str(errores).replace("'", "").upper()
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        raise UserError(str(log_msg))

                    # -----------------------------------------------------------------------------------------
                    # CODIGOS DE ERRORES DE WS validarComprobante QUE NO DETIENEN EL PROCESO DE FACTURACION
                    # GENERAN UNA ADVENTENCIA Y CONTINUAN EL PROCESO
                    # CUALQUIER ERROR NO LISTADO Y LOS ERRORES DE COMUNICACION Y RECEPCION DEL SRI NO DETIENEN
                    # EL PROCESO DE FACTURACION DE ODOO. SE EMITIRA EL RIDE Y XML SIN FECHA DE AUTORIZACION
                    # -----------------------------------------------------------------------------------------
                    # ----------------------------------------------------------------
                    # SI EL codigo_error == 70 --> CLAVE DE ACCESO EN PROCESAMIENTO O
                    # SI EL codigo_error == 43 --> CLAVE DE ACCESO REGISTRADA
                    # OTRO ERROR ES DE COMUNICACION Y NO DEBE PARAR EL PROCESO
                    # ----------------------------------------------------------------
                    if codigo_error != '70' and codigo_error != '43':
                        log_msg = 'SRI: PROBLEMAS DE COMUNICACION CON EL WS AL VALIDAR EL COMPROBANTE: ' + ' ' + str(errores).replace("'", "")
                    else:
                        log_msg = 'SRI: ADVERTENCIA AL VALIDAR EL COMPROBANTE: ' + ' ' + str(errores).replace("'", "")
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    raise UserError(str(log_msg))

                else:
                    # ---------------------------------------------------------------
                    # SI validador_recepcion == True --> ACTUALIZA EL LOG Y CONTINUA
                    # ---------------------------------------------------------------
                    log_msg = 'SRI: ENVIO ARCHIVO XML FIRMADO - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    log_msg = 'SRI: %s' % respuesta_sri + ' - (Ok)'
                    logging.info(log_msg)
                    self.history_log(log_msg)
                    if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                        self.estado_lc = "03"  # SRI AUTORIZACION PENDIENTE
                    else:
                        self.estado = "03"  # SRI AUTORIZACION PENDIENTE

        except Exception as error_message:
            log_msg = ''
            if 'PROBLEMAS DE COMUNICACION' in str(error_message):
                # ------------------------------------------------------------
                # PROBLEMAS DE COMUNICACION EN VALIDADOR DE RECEPCION DEL SRI
                # ------------------------------------------------------------
                if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                    self.estado_lc = "02"  # SRI AUTORIZACION PENDIENTE
                else:
                    self.estado = "02"  # SRI AUTORIZACION PENDIENTE

                return

            if 'ADVERTENCIA' in str(error_message):
                # -------------------------------------------------
                # ADVERTENCIA EN VALIDADOR DE RECEPCION DEL SRI
                # -------------------------------------------------
                if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                    self.estado_lc = "03"  # SRI AUTORIZACION PENDIENTE
                else:
                    self.estado = "03"  # SRI AUTORIZACION PENDIENTE

                return

            if 'ERROR' in str(error_message):
                # -------------------------------------------------
                # ERROR EN VALIDADOR DE RECEPCION DEL SRI
                # -------------------------------------------------

                raise UserError(str(log_msg))


    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def autorizar_comprobante_sri(self, inv_xml, tipo_comprobante_descripcion):
        # ------------------------------------------------------------------------------------------------------
        # SRI: AUTORIZAR COMPROBANTE
        # ------------------
        # noinspection PyProtectedMember
        url_recepcion, url_autorizacion = self.company_id._get_ws()
        fechaAutorizacion = {}

        try:
            if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                estado = self.estado_lc
            else:
                estado = self.estado
            if estado == "03":
                # --------------------------------
                # SOLICITA LA AUTORIZACION AL SRI
                # --------------------------------
                autorizacion, mensaje_autorizacion = inv_xml.request_authorization(self.doc_electronico_no_autorizacion, url_autorizacion)
                log_msg = 'SRI: SOLICITUD DE AUTORIZACION - (Ok)'
                logging.info(log_msg)
                self.history_log(log_msg)
                # --------------------------------------------------------------------------------------
                # SI autorizacion == False --> ERROR AL RECIBIR EL CODIGO DE AUTORIZACION DEL DOCUMENTO
                # mensaje_autorizacion CONTIENE EL MENSAJE DE ERROR
                # SE DETIENE EL PROCESO DE VALIDACION DEL self EN ODOO
                # --------------------------------------------------------------------------------------
                # ERROR DENTRO DE ESTE PROCESO DETIENE LA VALIDACION DEL FORMULARIO DE ODOO
                # --------------------------------------------------------------------------------------
                if not autorizacion:
                    msg = ' '.join(list(itertools.chain(*mensaje_autorizacion)))
                    log_msg = 'ERROR: SRI - AUTORIZAR COMPROBANTE REPORTA - ' + str(msg).replace("'", "").upper()
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                        self.estado_lc = "00"  # ERROR
                    else:
                        self.estado = "00"  # ERROR

                    return
                else:
                    # ---------------------------------------------------
                    # AÑADE LA AUTORIZACION DEL SRI AL DOCUMENTO FIRMADO
                    # ---------------------------------------------------
                    if mensaje_autorizacion == "SIN INFORMACION":
                        # ---------------------------------------------------------
                        # CLAVE DE ACCESO SIN REGISTRO EN EL SRI - SIN INFORMACION
                        # ---------------------------------------------------------
                        log_msg = 'SRI: AUTORIZAR COMPROBANTE: CLAVE DE ACCESO SIN REGISTRO EN EL SRI. POSIBLES PROBLEMAS DE COMUNICACION.\n\tINTENTAR MAS TARDE NUEVAMENTE'
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                            self.estado_lc = "02"  # SRI VALIDACION PENDIENTE
                        else:
                            self.estado = "02"  # SRI VALIDACION PENDIENTE

                    else:
                        # ---------------------------
                        # CLAVE DE ACCESO AUTORIZADA
                        # ---------------------------
                        autorizacion_xml = self.render_authorized_document(autorizacion)
                        # ---------------------------------------------
                        # EXTRAE fechaAutorizacion DESDE autorizacion_xml
                        # ---------------------------------------------
                        root = ET.fromstring(autorizacion_xml)
                        for autorizacion in root.iter('autorizacion'):
                            fechaAutorizacion = autorizacion.find('fechaAutorizacion').text
                        # -------------------------------------------------
                        # ACTUALIZA doc_electronico_fecha_autorizacion EN
                        # EL CORRESPONDIENTE self DE account.invoice
                        # ESTO PERMITE AÑADIR ESTA FECHA EN EL RIDE
                        # -------------------------------------------------
                        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                            vals = {
                                'doc_electronico_fecha_autorizacion_lc': fechaAutorizacion
                            }
                        else:
                            vals = {
                                'doc_electronico_fecha_autorizacion': fechaAutorizacion
                            }

                        forma = self.env['account.invoice'].search(
                            [('doc_electronico_no_autorizacion', '=', self.doc_electronico_no_autorizacion)])
                        forma.write(vals)

                        log_msg = 'SRI: DOCUMENTO AUTORIZADO - ' + fechaAutorizacion + ' - (Ok)'
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                            self.estado_lc = "04"  # SRI AUTORIZADO
                        else:
                            self.estado = "04"  # SRI AUTORIZADO

        except Exception as error_message:
            # -----------------------------------
            # WARNING EN PROCESO DE AUTORIZACION
            # -----------------------------------
            log_msg = 'SRI: ADVERTENCIA AL AUTORIZAR COMPROBANTE - ' + str(error_message).replace("'", "")
            logging.info(log_msg)
            self.history_log(log_msg)

            if tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                self.estado_lc = "03"  # SRI AUTORIZACION PENDIENTE
            else:
                self.estado = "03"  # SRI AUTORIZACION PENDIENTE

            return

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def procesar_individual(self):
        # -------------------------------------------------------
        # VALIDACION DE COMPROBANTES DE RETENCION EN CERO
        # -------------------------------------------------------
        if not self.bool_doc_enviado:
            return

        # ----------------------------------------------------------
        # VALIDACION DE EXISTENCIA DE CUENTAS DE CORREO ELECTRONICO
        # ----------------------------------------------------------
        correo_receptor = {}
        if self.company_id.email:
            correo_emisor = self.company_id.email.lower().replace(' ', '')
        else:
            error_message = "DIRECCION DE CORREO INEXISTENTE DE " + self.company_id.name
            log_msg = 'ERROR: PROCESO INDIVIDUAL - ' + str(error_message).replace("'", "").upper()
            logging.info(log_msg)
            self.history_log(log_msg)
            self.estado = "00"  # ERROR
            return

        if self.partner_id.email:
            correo_receptor = self.partner_id.email.lower().replace(' ', '')
        else:
            error_message = "DIRECCION DE CORREO INEXISTENTE DE " + self.partner_id.name
            log_msg = 'ODOO: ADVERTENCIA PROCESO INDIVIDUAL - ' + str(error_message).replace("'", "").upper()
            logging.info(log_msg)
            self.history_log(log_msg)

        # -------------------------------------------------------
        # VALIDACION DEL NUMERO DE CUENTAS DE CORREO ELECTRONICO
        # -------------------------------------------------------
        # no_emisor = len(correo_emisor.split(","))
        # no_receptor = len(correo_receptor.split(","))
        # if no_emisor > 1:
            # error_message = "EL EMISOR, DEBE TENER UNA SOLA CUENTA DE CORREO DE ENVIO (" + correo_emisor + ') ' + no_emisor
            # log_msg = 'ERROR: PROCESO INDIVIDUAL - ' + str(error_message).replace("'", "").upper()
            # logging.info(log_msg)
            # self.history_log(log_msg)
            # self.estado = "00"  # ERROR
            # return

        # -------------------------------------------------------
        # VALIDACION DE FORMATO DE CUENTAS DE CORREO ELECTRONICO
        # -------------------------------------------------------
        if correo_emisor:
            if not re.match('^[(a-z0-9\_\-\.)]+@[(a-z0-9\_\-\.)]+\.[(a-z)]{2,15}$', correo_emisor):
                error_message = "FORMATO INCORRECTO DE CORREO (" + correo_emisor + ') DE ' + self.company_id.name
                log_msg = 'ERROR: PROCESO INDIVIDUAL - ' + str(error_message).replace("'", "").upper()
                logging.info(log_msg)
                self.history_log(log_msg)
                self.estado = "00"  # ERROR
                return

        if correo_receptor:
            for correo in correo_receptor.split(","):
                if not re.match('^[(a-z0-9\_\-\.)]+@[(a-z0-9\_\-\.)]+\.[(a-z)]{2,15}$', correo):
                    error_message = "FORMATO INCORRECTO DE CORREO (" + correo + ') DE ' + self.partner_id.name
                    log_msg = 'ERROR: PROCESO INDIVIDUAL - ' + str(error_message).replace("'", "").upper()
                    logging.info(log_msg)
                    self.history_log(log_msg)
                    self.estado = "00"  # ERROR
                    return

        # -------------------------------------------------------------------
        # PROCESO DE VALIDACION DEL COMPROBANTE ELECTRONICO EN EL SRI
        # -------------------------------------------------------------------
        try:
            if self.tipo_comprobante_descripcion == 'LIQUIDACIÓN DE COMPRA':
                # -------------------------------
                # LIQUIDACION DE COMPRA
                # -------------------------------
                if self.estado == '00':
                    # ------
                    # ERROR
                    # ------
                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }

                if self.estado == '01':
                    # ----------------------
                    # RIDE & XML PENDIENTES
                    # ----------------------
                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml, archivo_firmado_xml = self.firma_electronica(self.tipo_comprobante_descripcion)
                    self.validar_comprobante_sri(inv_xml, archivo_firmado_xml, self.tipo_comprobante_descripcion)
                    self.autorizar_comprobante_sri(inv_xml, self.tipo_comprobante_descripcion)

                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml, archivo_firmado_xml = self.firma_electronica("COMPROBANTE DE RETENCION")
                    self.validar_comprobante_sri(inv_xml, archivo_firmado_xml, "COMPROBANTE DE RETENCION")
                    self.autorizar_comprobante_sri(inv_xml, "COMPROBANTE DE RETENCION")

                    # ---------------------------------------------
                    # SE REDEFINEN LOS ESTADOS. PREVALECE EL MENOR
                    # ---------------------------------------------
                    if int(self.estado) > int(self.estado_lc):
                        self.estado = self.estado_lc
                    else:
                        self.estado_lc = self.estado

                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }

                if self.estado == '02':
                    # -------------------------
                    # SRI VALIDACION PENDIENTE
                    # -------------------------
                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml = self.validar_xml(self.tipo_comprobante_descripcion)
                    adjuntos_ids = self.env['ir.attachment'].search([('name', '=', self.numero_autorizacion + '.xml')])
                    archivo_firmado_xml = base64.b64decode(adjuntos_ids.datas).decode('utf-8')
                    self.validar_comprobante_sri(inv_xml, archivo_firmado_xml, self.tipo_comprobante_descripcion)
                    self.autorizar_comprobante_sri(inv_xml, self.tipo_comprobante_descripcion)

                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml = self.validar_xml("COMPROBANTE DE RETENCION")
                    adjuntos_ids = self.env['ir.attachment'].search([('name', '=', self.doc_electronico_no_autorizacion + '.xml')])
                    archivo_firmado_xml = base64.b64decode(adjuntos_ids.datas).decode('utf-8')
                    self.validar_comprobante_sri(inv_xml, archivo_firmado_xml, "COMPROBANTE DE RETENCION")
                    self.autorizar_comprobante_sri(inv_xml, "COMPROBANTE DE RETENCION")

                    # ---------------------------------------------
                    # SE REDEFINEN LOS ESTADOS. PREVALECE EL MENOR
                    # ---------------------------------------------
                    if int(self.estado) > int(self.estado_lc):
                        self.estado = self.estado_lc
                    else:
                        self.estado_lc = self.estado

                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }

                if self.estado == '03':
                    # ---------------------------
                    # SRI AUTORIZACION PENDIENTE
                    # ---------------------------
                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml = self.validar_xml(self.tipo_comprobante_descripcion)
                    self.autorizar_comprobante_sri(inv_xml,  self.tipo_comprobante_descripcion)

                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml = self.validar_xml("COMPROBANTE DE RETENCION")
                    adjuntos_ids = self.env['ir.attachment'].search([('name', '=', self.doc_electronico_no_autorizacion + '.xml')])
                    archivo_firmado_xml = base64.b64decode(adjuntos_ids.datas).decode('utf-8')
                    self.validar_comprobante_sri(inv_xml, archivo_firmado_xml, "COMPROBANTE DE RETENCION")
                    self.autorizar_comprobante_sri(inv_xml, "COMPROBANTE DE RETENCION")

                    # ---------------------------------------------
                    # SE REDEFINEN LOS ESTADOS. PREVALECE EL MENOR
                    # ---------------------------------------------
                    if int(self.estado) > int(self.estado_lc):
                        self.estado = self.estado_lc
                    else:
                        self.estado_lc = self.estado

                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }

            else:
                # -------------------------------
                # FACTURA DE VENTA
                # NOTA DE CREDITO
                # COMPROBANTE DE RETENCION
                # -------------------------------
                if self.estado == '00':
                    # ------
                    # ERROR
                    # ------
                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }
                if self.estado == '01':
                    # ----------------------
                    # RIDE & XML PENDIENTES
                    # ----------------------
                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml, archivo_firmado_xml = self.firma_electronica(self.tipo_comprobante_descripcion)
                    self.validar_comprobante_sri(inv_xml, archivo_firmado_xml, self.tipo_comprobante_descripcion)
                    self.autorizar_comprobante_sri(inv_xml, self.tipo_comprobante_descripcion)
                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }

                if self.estado == '02':
                    # -------------------------
                    # SRI VALIDACION PENDIENTE
                    # -------------------------
                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml = self.validar_xml(self.tipo_comprobante_descripcion)
                    adjuntos_ids = self.env['ir.attachment'].search([('name', '=', self.doc_electronico_no_autorizacion + '.xml')])
                    archivo_firmado_xml = base64.b64decode(adjuntos_ids.datas).decode('utf-8')
                    self.validar_comprobante_sri(inv_xml, archivo_firmado_xml, self.tipo_comprobante_descripcion)
                    self.autorizar_comprobante_sri(inv_xml, self.tipo_comprobante_descripcion)
                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }

                if self.estado == '03':
                    # ---------------------------
                    # SRI AUTORIZACION PENDIENTE
                    # ---------------------------
                    log_msg = '–––––––––––––––––––– COMPROBANTE ELECTRONICO –––––––––––––––––––––'
                    logging.info(log_msg)
                    self.history_log(log_msg)

                    inv_xml = self.validar_xml(self.tipo_comprobante_descripcion)
                    self.autorizar_comprobante_sri(inv_xml, self.tipo_comprobante_descripcion)
                    # -------------------------------
                    # REFRESCA LA PANTALLA Y RETORNA
                    # -------------------------------
                    return {'type': 'ir.actions.client', 'tag': 'reload', }

        except Exception as error_message:
            # ------------------------------------------------------------------------------------
            # CUALQUIER ERROR DENTRO DE ESTE PROCESO DETIENE LA VALIDACION DEL FORMULARIO DE ODOO
            # ------------------------------------------------------------------------------------
            log_msg = str(error_message)
            logging.info(log_msg)

            if self.tipo_comprobante == '03' and self.estado_lc != '00':
                self.estado_lc = "00"  # ERROR
                self.estado = "00"  # ERROR
            else:
                self.estado = "00"  # ERROR
            return

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def procesar_listado(self):
        # ----------------------------------------------------
        # LLAMA A TODOS LOS FORMULARIOS PENDIENTES DE PROCESO
        # ----------------------------------------------------
        FORMULARIOS = self.env['account.invoice'].search([('estado', 'in', ['02', '03'])])

        log_msg = 'ODOO: INICIANDO VALIDACION MASIVA DE COMPROBANTES ELECTRONICOS PENDIENTES'
        logging.info(log_msg)

        # ---------------------------------------------
        # PROCESA UNO A UNO LOS FORMULARIOS PENDIENTES
        # ---------------------------------------------
        for formulario in FORMULARIOS:
            formulario.procesar_individual()

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def re_enviar_correo(self):
        try:
            if self.partner_id.email:
                # ------------------------------------------------------
                # SI EL DOCUMENTO ES UNA LIQUIDACION DE COMPRA LC
                # ------------------------------------------------------
                if self.tipo_comprobante == '03' and self.estado_lc != '00':
                    # ------------------------------------------------------
                    # ENVIA CORREO DE LIQUIDACION DE COMPRA
                    # ------------------------------------------------------
                    adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion_lc)])
                    if adjuntos_ids and self.message_attachment_count == 4:
                        self.send_document(
                            attachments=[a.ids for a in adjuntos_ids],
                            template='l10n_ec_invoice.email_template_purchase_clearance'
                        )
                        log_msg = 'ODOO: CORREO ELECTRONICO RE-ENVIADO A: ' + self.partner_id.email + ' - (Ok)'
                        logging.info(log_msg)
                        self.history_log(log_msg)
                    # ------------------------------------------------------
                    # ENVIA CORREO DEL COMPROBANTE DE RETENCION CR
                    # ------------------------------------------------------
                    adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
                    if adjuntos_ids and self.message_attachment_count == 4:
                        self.send_document(
                            attachments=[a.ids for a in adjuntos_ids],
                            template='l10n_ec_invoice.email_template_invoice'
                        )
                        log_msg = 'ODOO: CORREO ELECTRONICO RE-ENVIADO A: ' + self.partner_id.email + ' - (Ok)'
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        # --------------------------------------------------------------------------------
                        # MESSAGE_BOX CODE: USAR SOLO PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
                        # --------------------------------------------------------------------------------
                        title = "RE-ENVIO DE CORREO ELECTRONICO LC & CR:"
                        message = 'CORREOS ELECTRONICOS RE-ENVIADOS CON EXITO A: ' \
                                  + self.partner_id.email + ' PERTENECIENTE A:  ' + self.partner_id.name
                        view = self.env.ref('l10n_ec_invoice.message_box_form')
                        # view_id = view and view.id or False
                        context = dict(self._context or {})
                        context['message'] = message
                        return {'name': title, 'type': 'ir.actions.act_window', 'res_model': 'message_box',
                                'view_mode': 'form',
                                'view_type': 'form', 'view_id': view.id, 'target': 'new', 'context': context, }

                # ------------------------------------------------------
                # SI EL DOCUMENTO NO ES UNA LIQUIDACION DE COMPRA
                # ------------------------------------------------------
                if self.estado != '00':
                    # ---------------------------------------------------------
                    # ENVIA CORREO DEL COMPROBANTE ELECTRONICO: CR, FV, NC, GR
                    # ---------------------------------------------------------
                    adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
                    if adjuntos_ids and (self.message_attachment_count == 2 or self.message_attachment_count == 4):
                        self.send_document(
                            attachments=[a.ids for a in adjuntos_ids],
                            template='l10n_ec_invoice.email_template_invoice'
                        )
                        log_msg = 'ODOO: CORREO ELECTRONICO RE-ENVIADO A: ' + self.partner_id.email + ' - (Ok)'
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        # --------------------------------------------------------------------------------
                        # MESSAGE_BOX CODE: USAR SOLO PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
                        # --------------------------------------------------------------------------------
                        title = "RE-ENVIO DE CORREO ELECTRONICO:"
                        message = 'CORREO ELECTRONICO RE-ENVIADO CON EXITO A: ' \
                                  + self.partner_id.email + ' PERTENECIENTE A:  ' + self.partner_id.name
                        view = self.env.ref('l10n_ec_invoice.message_box_form')
                        # view_id = view and view.id or False
                        context = dict(self._context or {})
                        context['message'] = message
                        return {'name': title, 'type': 'ir.actions.act_window', 'res_model': 'message_box',
                                'view_mode': 'form',
                                'view_type': 'form', 'view_id': view.id, 'target': 'new', 'context': context, }

                    else:
                        log_msg = 'NO SE ENVIO EL CORREO A ' + self.partner_id.name + '. NUMERO DE ARCHIVOS ADJUNTOS ERRONEO. '
                        logging.info(log_msg)
                        self.history_log(log_msg)

                        # --------------------------------------------------------------------------------
                        # MESSAGE_BOX CODE: USAR SOLO PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
                        # --------------------------------------------------------------------------------
                        title = "RE-ENVIO DE CORREO ELECTRONICO:"
                        message = 'ADVERTENCIA: NO SE ENVIO EL CORREO A: ' + \
                                  self.partner_id.name + \
                                  '. NUMERO DE ARCHIVOS ADJUNTOS ERRONEO.'
                        view = self.env.ref('l10n_ec_invoice.message_box_form')
                        # view_id = view and view.id or False
                        context = dict(self._context or {})
                        context['message'] = message
                        return {'name': title, 'type': 'ir.actions.act_window', 'res_model': 'message_box',
                                'view_mode': 'form',
                                'view_type': 'form', 'view_id': view.id, 'target': 'new', 'context': context, }

                log_msg = 'NO SE ENVIO EL CORREO A ' + self.partner_id.name + '. RECEPTOR SIN DIRECCION. '
                logging.info(log_msg)
                self.history_log(log_msg)

                # --------------------------------------------------------------------------------
                # MESSAGE_BOX CODE: USAR SOLO PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
                # --------------------------------------------------------------------------------
                title = "RE-ENVIO DE CORREO ELECTRONICO:"
                message = 'ADVERTENCIA: NO SE ENVIO EL CORREO A: ' + \
                          self.partner_id.name + \
                          '. RECEPTOR SIN DIRECCION.'
                view = self.env.ref('l10n_ec_invoice.message_box_form')
                # view_id = view and view.id or False
                context = dict(self._context or {})
                context['message'] = message
                return {'name': title, 'type': 'ir.actions.act_window', 'res_model': 'message_box',
                        'view_mode': 'form',
                        'view_type': 'form', 'view_id': view.id, 'target': 'new', 'context': context, }

        except Exception as error_message:
            # ----------------------------------------------------------
            # ERROR EN ENVIO DE CORREO CON ARCHIVOS ADJUNTOS RIDE Y XML
            # ----------------------------------------------------------
            log_msg = 'ERROR: Envío de correo electrónico - ' + str(error_message).replace("'", "").upper()
            logging.info(log_msg)
            self.history_log(log_msg)
            self.estado = "00"  # ERROR
            return

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def replace_fix_chars(self, code):
        # ----------------------------------------------------------------------
        # REEMPLAZA LOS CARACTERES ESPECIALES POR CARACTERES COMUNES EN EL code
        # ----------------------------------------------------------------------
        special = [
            ['º', 'o'],
            ['Ñ', 'N'],
            ['ñ', 'n'],
            ['&', 'y'],
            ['á', 'a'],
            ['é', 'e'],
            ['í', 'i'],
            ['ó', 'o'],
            ['ú', 'u'],
            ['à', 'a'],
            ['è', 'e'],
            ['ì', 'i'],
            ['ò', 'o'],
            ['ù', 'u'],
            ['ü', 'u'],
            ['Á', 'A'],
            ['É', 'E'],
            ['Í', 'I'],
            ['Ó', 'O'],
            ['Ú', 'U'],
            ['À', 'A'],
            ['È', 'E'],
            ['Ì', 'I'],
            ['Ò', 'O'],
            ['Ù', 'U'],
            ['Ü', 'U'],
        ]
        if code:
            for f, r in special:
                code = code.replace(f, r)
        return code

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.one
    def add_attachment_xml(self, xml_element):

        nombre_archivo = ""
        attach_ids = []

        if self.tipo_documento_tributario == 'DOCUMENTO DE COMPRA':
            if 'liquidacionCompra' in xml_element:
                nombre_archivo = self.doc_electronico_no_autorizacion_lc
            else:
                nombre_archivo = self.doc_electronico_no_autorizacion
        if self.tipo_documento_tributario == 'FACTURA DE VENTA':
            nombre_archivo = self.doc_electronico_no_autorizacion
        if self.tipo_documento_tributario == 'NOTA DE CREDITO DE VENTA':
            nombre_archivo = self.doc_electronico_no_autorizacion
        if self.tipo_documento_tributario == 'GUIA DE REMISION':
            nombre_archivo = self.doc_electronico_no_autorizacion

        # ---------------------------------------------------------------------------------
        # ADICIONA LOS ARCHIVOS ADJUNTOS XML Y PDF AL FORMULARIO DEL DOCUMENTO ELECTRONICO
        # EN ESTE ESTADO GENERA LOS ARCHIVOS SIN LA AUTORIZACION DEL SRI
        # ---------------------------------------------------------------------------------
        # ------------
        # ARCHIVO XML
        # ------------
        buf = StringIO()
        buf.write(xml_element)
        document = base64.encodebytes(buf.getvalue().encode()).decode('ascii')
        buf.close()

        attach = self.env['ir.attachment'].create(
            {
                'name': '{0}.xml'.format(nombre_archivo),
                'datas': document,
                'datas_fname': '{0}.xml'.format(nombre_archivo),
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary'
            },
        )
        return attach_ids.append(attach)

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.one
    def add_attachment_pdf(self, xml_element):

        report_id = {}
        nombre_archivo = ""
        attach_ids = []
        ids = []

        if self.tipo_documento_tributario == 'DOCUMENTO DE COMPRA':
            if 'liquidacionCompra' in xml_element:
                report_id = 'l10n_ec_invoice.l10n_ec_invoice_purchase_clearance'
                nombre_archivo = self.doc_electronico_no_autorizacion_lc
            else:
                report_id = 'l10n_ec_invoice.l10n_ec_invoice_retention'
                nombre_archivo = self.doc_electronico_no_autorizacion
        if self.tipo_documento_tributario == 'FACTURA DE VENTA':
            report_id = 'l10n_ec_invoice.l10n_ec_invoice_out_invoice'
            nombre_archivo = self.doc_electronico_no_autorizacion
        if self.tipo_documento_tributario == 'NOTA DE CREDITO DE VENTA':
            report_id = 'l10n_ec_invoice.l10n_ec_invoice_out_refund'
            nombre_archivo = self.doc_electronico_no_autorizacion
        if self.tipo_documento_tributario == 'GUIA DE REMISION':
            report_id = 'l10n_ec_invoice.l10n_ec_invoice_delivery_guide'
            nombre_archivo = self.doc_electronico_no_autorizacion

        # ------------
        # ARCHIVO PDF
        # -----------------------------------------------------------------------------
        # self.tipo DEFINE EL TIPO DE REPORTE XML A USARSE PARA LA GENERACION DEL RIDE
        # -----------------------------------------------------------------------------
        ids.append(self.id)

        # datas = {'ids': ids, 'model': self._name}

        if report_id:
            attachment_obj = self.env['ir.attachment']

            # self.env.context.update({'type': 'binary'})

            pdf = self.env.ref(report_id)
            try:
                pdf = pdf.render_qweb_pdf(self.ids)
            except Exception as error_message:
                # ------------------------------------------------------------------------------------
                # CUALQUIER ERROR DENTRO DE ESTE PROCESO DETIENE LA VALIDACION DEL FORMULARIO DE ODOO
                # ------------------------------------------------------------------------------------
                log_msg = 'ERROR: (Añadir archivos) ' + str(error_message).replace("'", "").upper()
                logging.info(log_msg)
                self.history_log(log_msg)
                self.estado = "ERROR"
                return

            ride = base64.b64encode(pdf[0])
            attach = attachment_obj.create({
                'name': '{0}.pdf'.format(nombre_archivo),
                'type': 'binary',
                'datas': ride,
                'datas_fname': '{0}.pdf'.format(nombre_archivo),
                'res_model': self._name,
                'res_id': self.id,
            })
            attach_ids.append(attach)
        return attach_ids

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def send_document(self, attachments=None, template=False):
        template = self.env.ref(template)
        # ------------------------------------------------------------------------------------
        # attachments ES UNA LISTA CON LOS IDS DE LOS ATTACHMENTS AÑADIDOS
        # attach ES UNA TUPLA PARA INGRESAR EN attachment_ids DE LA FUNCION send_mail DE ODOO
        # ------------------------------------------------------------------------------------
        attach = ()
        for element in attachments:
            tuple_element = (element[0],)
            attach = attach + tuple_element
        msg_email = template.send_mail(
            self.id,
            force_send=False,
            raise_exception=True,
            email_values={
                'attachment_ids': attach
            },
        )
        if msg_email:
            return True
        else:
            return False

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def history_log(self, msg=None):
        utc_now = datetime.now()
        pst_now = utc_now.astimezone(pytz.timezone("America/Guayaquil"))
        Fecha_pst_now = pst_now.strftime("%d/%m/%Y %H:%M:%S")
        if not self.historial:
            self.historial = str(Fecha_pst_now) + ' - ' + str(msg) + '\n'
        else:
            self.historial = self.historial + str(Fecha_pst_now) + ' - ' + str(msg) + '\n'

    @staticmethod
    def render_authorized_document(autorizacion):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        edocument_tmpl = env.get_template('authorized_withdrawing.xml')
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': autorizacion.numeroAutorizacion,
            'ambiente': autorizacion.ambiente,
            'fechaAutorizacion': str(autorizacion.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S")),  # noqa
            'comprobante': autorizacion.comprobante
        }
        auth_withdrawing = edocument_tmpl.render(auth_xml)
        return auth_withdrawing

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def imprimir_comprobante(self):

        if self.estado_lc == '04' and self.doc_electronico_fecha_autorizacion_lc is False:
            # -----------------------------
            # UNLINK ELIMINA LOS PDFs creados
            # -----------------------------
            adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
            if adjuntos_ids:
                adjuntos_ids.unlink()

        if self.tipo_documento_tributario == 'FACTURA DE VENTA':
            return self.env.ref('l10n_ec_invoice.l10n_ec_invoice_out_invoice').report_action(self)
        if self.tipo_documento_tributario == 'NOTA DE CREDITO DE VENTA':
            return self.env.ref('l10n_ec_invoice.l10n_ec_invoice_out_refund').report_action(self)
        if self.tipo_documento_tributario == 'DOCUMENTO DE COMPRA':
            return self.env.ref('l10n_ec_invoice.l10n_ec_invoice_retention').report_action(self)

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def imprimir_liquidacion(self):

        if self.estado_lc == '04' and self.doc_electronico_fecha_autorizacion_lc is False:
            # -----------------------------
            # UNLINK ELIMINA LOS PDFs creados
            # -----------------------------
            adjuntos_ids = self.env['ir.attachment'].search([('name', 'like', self.doc_electronico_no_autorizacion)])
            if adjuntos_ids:

                adjuntos_ids.unlink()

        return self.env.ref('l10n_ec_invoice.l10n_ec_invoice_purchase_clearance').report_action(self)

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def mensaje_advertencia(self):
        # --------------------------------------------------------------------------------
        # MESSAGE_BOX CODE: USAR SOLO PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
        # --------------------------------------------------------------------------------
        title = "MENSAJE DE ADVERTENCIA:"
        message = 'El comprobante electrónico de este formulario no tiene la FECHA DE AUTORIZACION emitida ' + \
                  'por el SRI y su estado tributario es "SRI AUTORIZADO". Un primer uso de este procedimiento ' + \
                  'es para ingresar documentos de compra o venta con fechas anteriores a la fecha de inicio de ' + \
                  'la contabilidad. Un segundo uso para la presencia de la advertencia, se da cuando no se completa ' + \
                  'el proceso de facturación electronica de un formulario en el SRI y se procede a su ' + \
                  'reversion o anulación a través de cualesquiera de los procesos implementados por Odoo para este ' + \
                  'fin. Un tercer uso para esta advertencia es únicamente para indicar los Documentos de Compra que ' + \
                  'sido REVERSADOS.'
        view = self.env.ref('l10n_ec_invoice.message_box_form')
        # view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = message
        return {'name': title,
                'type': 'ir.actions.act_window',
                'res_model': 'message_box',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view.id,
                'target': 'new',
                'context': context,
                }

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def mensaje_error(self):
        # --------------------------------------------------------------------------------
        # MESSAGE_BOX CODE: USAR SOLO PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
        # --------------------------------------------------------------------------------
        title = "MENSAJE DE ERROR:"
        message = 'El Comprobante Electrónico de este Formulario contiene un ERROR IMPORTANTE y debe ser atendido ' \
                  'a la brevedad posible.'
        view = self.env.ref('l10n_ec_invoice.message_box_form')
        # view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = message
        return {'name': title,
                'type': 'ir.actions.act_window',
                'res_model': 'message_box',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view.id,
                'target': 'new',
                'context': context,
                }

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def mensaje_numero_autorizacion(self):
        # --------------------------------------------------------------------------------
        # MESSAGE_BOX CODE: USAR SOLO PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
        # --------------------------------------------------------------------------------
        title = "MENSAJE INFORMATIVO:"
        message = 'Se debe cambiar el "Número de Autorización" del formulario.'
        view = self.env.ref('l10n_ec_invoice.message_box_form')
        # view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = message
        return {'name': title,
                'type': 'ir.actions.act_window',
                'res_model': 'message_box',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view.id,
                'target': 'new',
                'context': context,
                }
