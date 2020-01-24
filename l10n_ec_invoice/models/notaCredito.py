# -*- coding: utf-8 -*-

# -------------------------------------------------------------------------
# Ecuador Invoice
# Localización para Odoo V12
# Por: Oodca Sociedad Anónima © <2019> <José Enríquez>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -------------------------------------------------------------------------

# ---------------------------
# Notes:    LIBRERIAS PYTHON
# ---------------------------
# noinspection PyUnresolvedReferences
from odoo import api, fields, models
from datetime import datetime

import pytz
import xml.etree.ElementTree as ET


# ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
#   O   OOOOO OOOOO OOOOO O   O O   O OOOOO     OOO  O   O O   O OOOOO  OOO  OOOOO OOOOO
#  O O  O     O     O   O O   O OO  O   O        O   OO  O O   O O   O   O   O     O
# O   O O     O     O   O O   O O O O   O        O   O O O O   O O   O   O   O     OOO
# OOOOO O     O     O   O O   O O  OO   O        O   O  OO  O O  O   O   O   O     O
# O   O OOOOO OOOOO OOOOO OOOOO O   O   O       OOO  O   O   O   OOOOO  OOO  OOOOO OOOOO
# ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def archivo_notaCredito_xml(self):
        nombreComercial = {}
        infoAdicional = {}
        # ---------------------------------
        # SE ACTUALIZA EL NO DE REFERENCIA
        # ---------------------------------
        journal = self.journal_id
        sequence = journal.notaCredito_sequence_id

        notaCredito_sequence_number_next = journal.notaCredito_sequence_number_next

        establecimiento = journal.establecimiento
        punto_emision = journal.punto_emision
        numero_secuencial = "0" * (9 - len(str(notaCredito_sequence_number_next))) + str(notaCredito_sequence_number_next)

        reference = establecimiento + "-" + punto_emision + "-" + numero_secuencial

        formularioOrigen = self.env['account.invoice'].search([('number', '=', self.origin)])
        # ------------------------------------------------------------------------------------
        # FECHAS: La fecha de la notaCredito debe ser la fecha de emisión del documento de compra
        # Si fue determinada por el usuario se mantiene
        # ------------------------------------------------------------------------------------
        if not self.doc_electronico_fecha:
            fecha_documento_electronico = self.date_invoice
        else:
            fecha_documento_electronico = self.doc_electronico_fecha

        # --------------
        # DECLARACIONES
        # --------------
        contribuyenteEspecial = {}
        nombreComercial_company = self.env['res.partner'].search([('id', '=', self.company_id.id)]).nombre_comercial
        ruta_archivo_xml = self.company_id.company_ruta_documentos
        doc_electronico_xml = "NC-" + reference + ".xml"
        nombre_archivo = ruta_archivo_xml + doc_electronico_xml
        # ----------------------------------------------
        # Fecha FECHA DE EMISION CON FORMATO dd/mm/aaaa
        # ----------------------------------------------
        Fecha_str = str(self.date_invoice)
        Fecha_obj = datetime.strptime(Fecha_str, '%Y-%m-%d').date()
        # Fecha = Fecha_obj.strftime("%d/%m/%Y")
        # ---------------------------------
        # clave_de_autorizacion GENERACION
        # -----------------------------------------------------------------------
        # SE DEFINE EL codigo_numerico SEMANA HORA MINUTO SEGUNDO Ejmp: 30122436
        # -----------------------------------------------------------------------
        utc_now = datetime.today()
        pst_now = utc_now.astimezone(pytz.timezone("America/Guayaquil"))
        codigo_numerico_semana = str('{:02}'.format(int(pst_now.strftime("%U"))))
        codigo_numerico_hora_dia = str('{:02}'.format(int(pst_now.strftime("%H"))))
        codigo_numerico_minuto_dia = str('{:02}'.format(int(pst_now.strftime("%M"))))
        codigo_numerico_segundo_hora = str('{:02}'.format(int(pst_now.strftime("%S"))))
        codigo_numerico = codigo_numerico_semana \
                          + codigo_numerico_hora_dia \
                          + codigo_numerico_minuto_dia \
                          + codigo_numerico_segundo_hora

        # noinspection PyUnusedLocal
        Fecha_pst_now = pst_now.strftime("%d/%m/%Y %H:%M:%S")

        # ----------------------------------------------------------
        # SE DEFINE LA clave_autorizacion SIN EL DIGITO VERIFICADOR
        # ----------------------------------------------------------
        clave_autorizacion0 = str('{:02}'.format(Fecha_obj.day)) + \
                              str('{:02}'.format(Fecha_obj.month)) + \
                              str(Fecha_obj.year)                       # 8D FECHA DE EMISION DDMMAAAA
        clave_autorizacion1 = "04"                                      # 2D TIPO DE COMPROBANTE 01 NOTA DE VENTA
        clave_autorizacion2 = self.company_id.vat                       # 13D NUMERO RUC 1704172269001
        clave_autorizacion3 = self.company_id.env_service               # 1D TIPO AMBIENTE 1 O 2 PRUEBAS O PRODUCCION
        clave_autorizacion4 = establecimiento + punto_emision           # 6D SERIE 001002 ESTABLECIMIENTO Y PUNTO DE EMISION
        clave_autorizacion5 = numero_secuencial                         # 9D NUMERO DEL COMPROBANTE SECUENCIAL
        clave_autorizacion6 = codigo_numerico                           # 8D CODIGO NUMERICO
        clave_autorizacion7 = "1"                                       # 1D TIPO DE EMISION 1 NORMAL

        clave_autorizacion = clave_autorizacion0 + clave_autorizacion1 + clave_autorizacion2 + clave_autorizacion3 + \
                             clave_autorizacion4 + clave_autorizacion5 + clave_autorizacion6 + clave_autorizacion7
        # ----------------------------------------------------
        # SE INGRESA EL FACTOR DE CHEQUEO PONDERADO MODULO 11
        # ----------------------------------------------------
        factor_chequeo_ponderado = "765432765432765432765432765432765432765432765432"
        # -------------------------------
        # SE DEFINE EL digitoVerificador
        # -------------------------------
        index = 0
        suma = 0
        for n in factor_chequeo_ponderado:
            suma = suma + int(n) * int(clave_autorizacion[index])
            index = index + 1
        residuo = suma % 11
        if residuo == 0:
            digitoVerificador = 0
        elif residuo == 1:
            digitoVerificador = 1
        else:
            digitoVerificador = 11 - residuo
        # ----------------------------------------------------------
        # SE DEFINE LA clave_autorizacion CON EL DIGITO VERIFICADOR
        # ----------------------------------------------------------
        clave_autorizacion = clave_autorizacion + str(digitoVerificador)
        # ---------------------------------
        # notaCredito XML ESTRUCTURA PRINCIPAL
        # ---------------------------------
        notaCredito = ET.Element("notaCredito")
        infoTributaria = ET.SubElement(notaCredito, "infoTributaria")
        infoNotaCredito = ET.SubElement(notaCredito, "infoNotaCredito")
        detalles = ET.SubElement(notaCredito, "detalles")
        if self.partner_id.email:
            infoAdicional = ET.SubElement(notaCredito, "infoAdicional")
        # :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        # ------------------------
        # notaCredito XML INFORMACION
        # ------------------------
        notaCredito.set('id', 'comprobante')
        notaCredito.set('version', '1.0.0')
        # ------------------------------
        # infoTributaria XML ESTRUCTURA
        # ------------------------------
        ambiente = ET.SubElement(infoTributaria, "ambiente")
        tipoEmision = ET.SubElement(infoTributaria, "tipoEmision")
        razonSocial = ET.SubElement(infoTributaria, "razonSocial")
        # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        if nombreComercial_company:
            nombreComercial = ET.SubElement(infoTributaria, "nombreComercial")
        # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        ruc = ET.SubElement(infoTributaria, "ruc")
        claveAcceso = ET.SubElement(infoTributaria, "claveAcceso")
        codDoc = ET.SubElement(infoTributaria, "codDoc")
        estab = ET.SubElement(infoTributaria, "estab")
        ptoEmi = ET.SubElement(infoTributaria, "ptoEmi")
        secuencial = ET.SubElement(infoTributaria, "secuencial")
        dirMatriz = ET.SubElement(infoTributaria, "dirMatriz")
        # ----------------------
        # infoTributaria TEXTOS
        # ----------------------
        ambiente.text = "1"
        tipoEmision.text = "1"
        razonSocial.text = self.company_id.name
        # :::::::::::::::::::::::::::::::::::::::::
        if nombreComercial_company:
            nombreComercial.text = nombreComercial_company
        # :::::::::::::::::::::::::::::::::::::::::
        ruc.text = self.company_id.vat
        claveAcceso.text = clave_autorizacion
        codDoc.text = "04"
        estab.text = establecimiento
        ptoEmi.text = punto_emision
        secuencial.text = numero_secuencial
        dirMatriz.text = self.company_id.street
        # -------------------------------
        # infoNotaCredito XML ESTRUCTURA
        # -------------------------------
        fechaEmision = ET.SubElement(infoNotaCredito, "fechaEmision")
        dirEstablecimiento = ET.SubElement(infoNotaCredito, "dirEstablecimiento")
        tipoIdentificacionComprador = ET.SubElement(infoNotaCredito, "tipoIdentificacionComprador")
        razonSocialComprador = ET.SubElement(infoNotaCredito, "razonSocialComprador")
        identificacionComprador = ET.SubElement(infoNotaCredito, "identificacionComprador")
        # :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        if self.company_id.company_contribuyente_especial == "SI":
            contribuyenteEspecial = ET.SubElement(infoNotaCredito, "contribuyenteEspecial")
        # :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        obligadoContabilidad = ET.SubElement(infoNotaCredito, "obligadoContabilidad")
        # :::::::::::::::::::::::::::::::::::::::::::::::::::::::
        if self.fiscal_position_id.name == "Contribuyente RISE":
            # noinspection PyUnusedLocal
            rise = ET.SubElement(infoNotaCredito, "rise")
        # :::::::::::::::::::::::::::::::::::::::::::::::::::::::
        codDocModificado = ET.SubElement(infoNotaCredito, "codDocModificado")
        numDocModificado = ET.SubElement(infoNotaCredito, "numDocModificado")
        fechaEmisionDocSustento = ET.SubElement(infoNotaCredito, "fechaEmisionDocSustento")
        totalSinImpuestos = ET.SubElement(infoNotaCredito, "totalSinImpuestos")
        valorModificacion = ET.SubElement(infoNotaCredito, "valorModificacion")
        moneda = ET.SubElement(infoNotaCredito, "moneda")
        # -----------------------
        # infoNotaCredito TEXTOS
        # -----------------------
        Fecha_str = str(self.date_invoice)
        Fecha_obj = datetime.strptime(Fecha_str, '%Y-%m-%d').date()
        Fecha = Fecha_obj.strftime("%d/%m/%Y")
        fechaEmision.text = Fecha
        dirEstablecimiento.text = self.company_id.street
        tipoIdentificacionComprador.text = "04"
        if self.partner_id.tipo_identidad == "ruc":
            tipoIdentificacionComprador.text = "04"
        if self.partner_id.tipo_identidad == "cedula":
            tipoIdentificacionComprador.text = "05"
        if self.partner_id.tipo_identidad == "pasaporte":
            tipoIdentificacionComprador.text = "06"
        razonSocialComprador.text = self.partner_id.name
        identificacionComprador.text = self.partner_id.numero_identidad
        # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        if self.company_id.company_contribuyente_especial == "SI":
            contribuyenteEspecial.text = self.company_id.company_registry
        # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        obligadoContabilidad.text = self.company_id.company_obligado_contabilidad
        # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        rise = {}
        if self.fiscal_position_id.name == "Contribuyente RISE":
            rise.text = "Contribuyente Régimen Simplificado RISE"
        # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::
        codDocModificado.text = "01"
        numDocModificado.text = formularioOrigen.reference
        Fecha_str = str(formularioOrigen.date_invoice)
        Fecha_obj = datetime.strptime(Fecha_str, '%Y-%m-%d').date()
        Fecha = Fecha_obj.strftime("%d/%m/%Y")
        fechaEmisionDocSustento.text = Fecha
        totalSinImpuestos.text = str('{:.2f}'.format(self.amount_untaxed))
        valorModificacion.text = str('{:.2f}'.format(self.amount_total))
        moneda.text = "DOLAR"
        # -----------------------------------------------------
        # totalConImpuestos XML ESTRUCTURA --> infoNotaCredito
        # -----------------------------------------------------
        # subtotal_0
        # subtotal_12
        # subtotal_no_sujeto_iva
        # ice
        # irbpnr
        totalConImpuestos = ET.SubElement(infoNotaCredito, "totalConImpuestos")
        # -------------------------
        # totalImpuesto subtotal_0
        # -------------------------
        if self.subtotal_0 != 0.00:
            codigo_tabla_16 = "2"                                           # IVA código TABLA 16 es 2
            tax_tarifa = "0"                                                # tarifa es 0
            codigo_tabla_17 = "0"                                           # IVA 0% código TABLA 17 es 0
            # ---------------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalConImpuestos
            # ---------------------------------------------------
            totalImpuesto = ET.SubElement(totalConImpuestos, "totalImpuesto")
            # -----------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalImpuesto
            # -----------------------------------------------
            codigo = ET.SubElement(totalImpuesto, "codigo")
            codigoPorcentaje = ET.SubElement(totalImpuesto, "codigoPorcentaje")
            baseImponible = ET.SubElement(totalImpuesto, "baseImponible")
            valor = ET.SubElement(totalImpuesto, "valor")
            # ---------------------
            # totalImpuesto TEXTOS
            # ---------------------
            codigo.text = codigo_tabla_16
            codigoPorcentaje.text = codigo_tabla_17
            baseImponible.text = str('{:.2f}'.format(self.subtotal_0))
            valor.text = str('{:.2f}'.format(round(float(baseImponible.text) * float(tax_tarifa.replace(' ', '')) / 100, 2)))
        # --------------------------
        # totalImpuesto subtotal_12
        # --------------------------
        if self.subtotal_12 != 0.00:
            codigo_tabla_16 = "2"                                           # IVA código TABLA 16 es 2
            tax_tarifa = "12"                                               # tarifa es 0
            codigo_tabla_17 = "2"                                           # IVA 12% código TABLA 17 es 0
            # ---------------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalConImpuestos
            # ---------------------------------------------------
            totalImpuesto = ET.SubElement(totalConImpuestos, "totalImpuesto")
            # -----------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalImpuesto
            # -----------------------------------------------
            codigo = ET.SubElement(totalImpuesto, "codigo")
            codigoPorcentaje = ET.SubElement(totalImpuesto, "codigoPorcentaje")
            baseImponible = ET.SubElement(totalImpuesto, "baseImponible")
            valor = ET.SubElement(totalImpuesto, "valor")
            # ---------------------
            # totalImpuesto TEXTOS
            # ---------------------
            codigo.text = codigo_tabla_16
            codigoPorcentaje.text = codigo_tabla_17
            baseImponible.text = str('{:.2f}'.format(self.subtotal_12))
            valor.text = str('{:.2f}'.format(round(float(baseImponible.text) * float(tax_tarifa.replace(' ', '')) / 100, 2)))
        # -------------------------------------
        # totalImpuesto subtotal_no_sujeto_iva
        # -------------------------------------
        if self.subtotal_no_sujeto_iva != 0.00:
            codigo_tabla_16 = "2"                                           # IVA código TABLA 16 es 2
            tax_tarifa = "0"                                                # tarifa es 0
            codigo_tabla_17 = "6"                                           # IVA 12% código TABLA 17 es 0
            # ---------------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalConImpuestos
            # ---------------------------------------------------
            totalImpuesto = ET.SubElement(totalConImpuestos, "totalImpuesto")
            # -----------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalImpuesto
            # -----------------------------------------------
            codigo = ET.SubElement(totalImpuesto, "codigo")
            codigoPorcentaje = ET.SubElement(totalImpuesto, "codigoPorcentaje")
            baseImponible = ET.SubElement(totalImpuesto, "baseImponible")
            valor = ET.SubElement(totalImpuesto, "valor")
            # ---------------------
            # totalImpuesto TEXTOS
            # ---------------------
            codigo.text = codigo_tabla_16
            codigoPorcentaje.text = codigo_tabla_17
            baseImponible.text = str('{:.2f}'.format(self.subtotal_no_sujeto_iva))
            valor.text = str('{:.2f}'.format(round(float(baseImponible.text) * float(tax_tarifa.replace(' ', '')) / 100, 2)))
        # ------------------
        # totalImpuesto ice
        # ------------------
        if self.ice != 0.00:
            codigo_tabla_16 = "3"                                           # ICE código TABLA 16 es 3
            tax_tarifa = "15"                                               # tarifa es 15 - CAMBIAR SI ES NECESARIO
            codigo_tabla_17 = "3610"                                        # ICE 15% código TABLA 17 es 3610
            # ---------------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalConImpuestos
            # ---------------------------------------------------
            totalImpuesto = ET.SubElement(totalConImpuestos, "totalImpuesto")
            # -----------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalImpuesto
            # -----------------------------------------------
            codigo = ET.SubElement(totalImpuesto, "codigo")
            codigoPorcentaje = ET.SubElement(totalImpuesto, "codigoPorcentaje")
            baseImponible = ET.SubElement(totalImpuesto, "baseImponible")
            valor = ET.SubElement(totalImpuesto, "valor")
            # ---------------------
            # totalImpuesto TEXTOS
            # ---------------------
            codigo.text = codigo_tabla_16
            codigoPorcentaje.text = codigo_tabla_17
            baseImponible.text = str('{:.2f}'.format(self.ice))
            valor.text = str('{:.2f}'.format(round(float(baseImponible.text) * float(tax_tarifa.replace(' ', '')) / 100, 2)))
        # ---------------------
        # totalImpuesto irbpnr
        # ---------------------
        if self.irbpnr != 0.00:
            codigo_tabla_16 = "4"                                           # IRBPNR código TABLA 16 es 4
            tax_tarifa = "0.02"                                             # tarifa es 15 - CAMBIAR SI ES NECESARIO
            codigo_tabla_17 = "5001"                                        # IRBPNR 15% código TABLA 17 es 3610
            # ---------------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalConImpuestos
            # ---------------------------------------------------
            totalImpuesto = ET.SubElement(totalConImpuestos, "totalImpuesto")
            # -----------------------------------------------
            # totalImpuesto XML ESTRUCTURA --> totalImpuesto
            # -----------------------------------------------
            codigo = ET.SubElement(totalImpuesto, "codigo")
            codigoPorcentaje = ET.SubElement(totalImpuesto, "codigoPorcentaje")
            baseImponible = ET.SubElement(totalImpuesto, "baseImponible")
            valor = ET.SubElement(totalImpuesto, "valor")
            # ---------------------
            # totalImpuesto TEXTOS
            # ---------------------
            codigo.text = codigo_tabla_16
            codigoPorcentaje.text = codigo_tabla_17
            baseImponible.text = str('{:.2f}'.format(self.irbpnr))
            valor.text = str('{:.2f}'.format(round(float(baseImponible.text) * float(tax_tarifa.replace(' ', '')) / 100, 2)))
        # ----------------------------------------------------------------
        # infoNotaCredito XML ESTRUCTURA --> infoNotaCredito CONTINUACION
        # ----------------------------------------------------------------
        motivo = ET.SubElement(infoNotaCredito, "motivo")
        # --------------
        # motivo TEXTOS
        # --------------
        motivo.text = "DEVOLUCION"

        for line in self.mapped('invoice_line_ids'):
            if line.price_subtotal != 0:
                # ------------------------
                # detalles ESTRUCTURA XML
                # ------------------------
                detalle = ET.SubElement(detalles, "detalle")
                # ------------------------------------------------------------
                # codigoPrincipal, descripcion etc XML ESTRUCTURA --> detalle
                # ------------------------------------------------------------
                codigoInterno = ET.SubElement(detalle, "codigoInterno")
                descripcion = ET.SubElement(detalle, "descripcion")
                cantidad = ET.SubElement(detalle, "cantidad")
                precioUnitario = ET.SubElement(detalle, "precioUnitario")
                descuento = ET.SubElement(detalle, "descuento")
                precioTotalSinImpuesto = ET.SubElement(detalle, "precioTotalSinImpuesto")
                # --------------------------------------------------------------
                # NO SE INCLUYE Ejemplo:
                # <detallesAdicionales>
                #     <detalleAdicional nombre="Marca" valor="Chevrolet"/>
                #     <detAdicional nombre="Modelo" valor="2012"/>
                #     <detAdicional nombre="Chasis" valor="8LDETA03V20003289"/>
                # </detallesAdicionales>
                # --------------------------------------------------------------
                # ----------------------------------------
                # codigoPrincipal, descripcion etc TEXTOS
                # ----------------------------------------
                codigoInterno.text = self.env['product.product'].search([('id', '=', line.product_id.id)]).barcode
                descripcion.text = line.name
                cantidad.text = str(line.quantity)
                precioUnitario.text = str(line.price_unit)
                descuento.text = str('{:.2f}'.format(round(line.quantity * line.price_unit * line.discount / 100, 2)))
                precioTotalSinImpuesto.text = str('{:.2f}'.format(line.price_subtotal))

                taxes = line.invoice_line_tax_ids
                codigo_tabla_16 = {}
                codigo_tabla_17_18 = {}
                # -------------------------
                # impuestos ESTRUCTURA XML
                # -------------------------
                impuestos = ET.SubElement(detalle, "impuestos")
                for tax in taxes:
                    tax_type = tax.name[0:3]
                    tax_tarifa = tax.name[3:6]
                    tax_name = tax.name[9:17]

                    if tax_type == "IVA":
                        codigo_tabla_16 = "2"
                    if tax_type == "ICE":
                        codigo_tabla_16 = "3"
                    if tax_type == "IRB":
                        codigo_tabla_16 = "4"

                    if tax_type == "IVA" and tax_tarifa == " 00" and tax_name == "VenLocal":
                        codigo_tabla_17_18 = "0"
                    if tax_type == "IVA" and tax_tarifa == " 12" and tax_name == "VenLocal":
                        codigo_tabla_17_18 = "2"
                    if tax_type == "IVA" and tax_tarifa == " 00" and tax_name == "VenNoObj":
                        codigo_tabla_17_18 = "6"
                    if tax_type == "IVA" and tax_tarifa == " 00" and tax_name == "VenExent":
                        codigo_tabla_17_18 = "7"
                    # -----------------------------------
                    # AÑADIR LOS CODIGOS QUE SE NECESITE
                    # -----------------------------------
                    if tax_type == "ICE" and tax_tarifa == "150" and tax_name == "VenIVA12":
                        codigo_tabla_17_18 = "3023"
                    # ------------------------
                    # impuesto XML ESTRUCTURA
                    # -----------------------
                    impuesto = ET.SubElement(impuestos, "impuesto")
                    # ------------------------------------------------------------
                    # codigoPrincipal, descripcion etc XML ESTRUCTURA --> detalle
                    # ------------------------------------------------------------
                    codigo = ET.SubElement(impuesto, "codigo")
                    codigoPorcentaje = ET.SubElement(impuesto, "codigoPorcentaje")
                    tarifa = ET.SubElement(impuesto, "tarifa")
                    baseImponible = ET.SubElement(impuesto, "baseImponible")
                    valor = ET.SubElement(impuesto, "valor")
                    # ---------------------------------------------------------------
                    # codigo, codigoPorcentaje, tarifa, baseImponible & valor TEXTOS
                    # ---------------------------------------------------------------
                    codigo.text = codigo_tabla_16
                    codigoPorcentaje.text = codigo_tabla_17_18
                    tarifa.text = tax_tarifa.replace(' ', '')
                    baseImponible.text = str('{:.2f}'.format(line.price_subtotal))
                    valor.text = str('{:.2f}'.format(round(float(tarifa.text) * float(baseImponible.text) / 100, 2)))
        # ----------------------
        # campoAdicional  TEXTO
        # ----------------------
        if self.partner_id.email:
            campoAdicional = ET.SubElement(infoAdicional, "campoAdicional")
            campoAdicional.set('nombre', 'Email')
            campoAdicional.text = self.partner_id.email
        # ---------------------------
        # GENERACION DEL ARCHIVO XML
        # ---------------------------
        tree = ET.ElementTree(notaCredito)
        tree.write(nombre_archivo, encoding='utf-8', xml_declaration=True)
        # ---------------------------------------
        # SE GUARDA EN LA BASE DE DATOS LA NUEVA
        # SECUENCIA notaCredito_sequence_number_next
        # ---------------------------------------
        vals = {'notaCredito_sequence_number_next': notaCredito_sequence_number_next + sequence.number_increment}
        journal.write(vals)

        # ------------------------------
        # SE GUARDA EN LA BASE DE DATOS
        # doc_electronico_no
        # doc_electronico_fecha
        # doc_electronico_xml
        # bool_doc_enviado
        # bool_onOff_generar
        # ------------------------------
        vals = {
            'reference': reference,
            'doc_electronico_no': reference,
            'doc_electronico_fecha': fecha_documento_electronico,
            'doc_electronico_no_autorizacion': clave_autorizacion,
            'doc_electronico_xml': doc_electronico_xml,
            'bool_doc_enviado': True,
            'numero_autorizacion': clave_autorizacion
        }
        formulario = self.env['account.invoice'].search([('id', '=', self.id)])
        formulario.write(vals)

        self.validar_xml(self.tipo_comprobante_descripcion)
