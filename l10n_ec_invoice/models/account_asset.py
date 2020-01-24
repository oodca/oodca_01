# -*- coding: utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

# -------------------------------------------------------------------------
# Ecuador Invoice
# Localización para Odoo V12
# Por: Oodca Sociedad Anónima © <2019> <José Enríquez>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -------------------------------------------------------------------------

# -----------------
# LIBRERIAS PYTHON
# -----------------

# noinspection PyUnresolvedReferences,PyProtectedMember
from odoo import api, fields, models, _

from datetime import datetime

# noinspection PyUnresolvedReferences
from odoo.exceptions import (
    AccessDenied, RedirectWarning, MissingError, except_orm,
    AccessError, DeferredException, ValidationError, Warning
    as UserError
)


# ----------------------------------------------------------------------------------------------------------------------
#  OOOO O       O    OOOO  OOOO      O  O   O O   O OOOOO OOOO   O  OOOOO
# O     O      O O  O     O          O  OO  O O   O O     O   O  O    O
# O     O     O   O  OOO   OOO       O  O O O OOOOO OOO   OOOO   O    O
# O     O     OOOOO     O     O      O  O  OO O   O O     O  O   O    O
#  OOOO OOOOO O   O OOOO  OOOO       O  O   O O   O OOOOO O   O  O    O
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
#   O    OOOO  OOOO  OOO  O   O O   O OOOOO       O    OOOO  OOOO 00000 OOOOO      O    OOOO  OOOO 00000 OOOOO
#  O O  O     O     O   O O   O OO  O   O        O O  O     O     O       O       O O  O     O     O       O
# O   O O     O     O   O O   O O O O   O       O   O  OOO   OOO  OOO     O      O   O  OOO   OOO  OOO     O
# OOOOO O     O     O   O O   O O  OO   O       OOOOO     O     O O       O      OOOOO     O     O O       O
# O   O  OOOO  OOOO  OOO   OOO  O   O   O       O   O OOOO  OOOO  OOOOO   O      O   O OOOO  OOOO  OOOOO   O
# ----------------------------------------------------------------------------------------------------------------------
class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'
    # ---------------------
    # DEFINICION DE CAMPOS
    # ---------------------
    factura_id = fields.Many2one(
        'account.invoice',
        string='Ver factura',
    )
    factura_ids = fields.Many2many(
        'account.invoice',
        string='Fusionar activos',
    )
    factura_memoria = fields.Char(
        string='Memoria',
        help='Memoriza los ids de las facturas fusionadas en este activo',
    )
    diario_id = fields.Many2one(
        'account.move',
        string='Diario Contable',
    )
    cuenta_credito_id = fields.Many2one(
        'account.account',
        string='Cuenta Débito',
        default=79,
    )

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.onchange('factura_ids')
    def _compute_gross_value(self):
        # ----------------------------------------------
        # CALCULA EL VALOR TOTAL DEL ACTIVO COSTO + IVA
        # Y SE ASIGNA ESTE A self.value
        # DE TODAS LAS FACTURAS AÑADIDAS
        # ----------------------------------------------
        self.value = 0
        for factura_id in self.factura_ids:
            # ---------------------------
            # ASIGNA VALORES POR DEFECTO
            # ---------------------------
            self.partner_id = factura_id.partner_id
            self.factura_id = factura_id
            number = factura_id.number
            FACTURAS = self.env['account.invoice'].search([('number', '=', number)])
            for factura in FACTURAS:
                for line in factura.mapped('invoice_line_ids'):
                    # --------------------
                    # SE CALCULA EL COSTO
                    # --------------------
                    if line.account_id.user_type_id.id == 6:
                        self.value = self.value + line.price_subtotal
                        for tax in line.invoice_line_tax_ids:
                            # ------------------
                            # SE CALCULA EL IVA
                            # ------------------
                            tipo_impuesto = tax.name[0:3]
                            if tipo_impuesto == 'IVA':
                                # ------------------------------------
                                # IMPUESTO AL VALOR AGREGADO IVA
                                # ------------------------------------
                                #  ___3__3 _2_______81 ___4
                                #  IVA 12 bsComLocalC 510
                                #  IVA 12 afComLocalC 511
                                #  IVA 00 bsComLocalC 517
                                #  abc999 ababcdefgha 999a
                                #  -----------------------
                                #  01234567890123456789012
                                # ------------------------
                                porcentaje_impuesto = int(tax.name[3:6])
                                self.value = self.value + porcentaje_impuesto * line.price_subtotal / 100
        # ----------------------------------------------------------------------------
        # CONTROL DE QUE FACTURAS DEBEN APARECER COMO DISPONIBLES PARA SER FUSIONADAS
        # A TRAVES DE LA VARIABLE bool_activo_no_corriente
        # ESTE CONTROLA CUANDO SON FUSIONADAS O CUANDO SON RETIRADAS
        # ----------------------------------------------------------------------------
        factura_memoria_lista = {}
        if not self.factura_memoria:
            numero_facturas_memoria = 0
        else:
            factura_memoria_lista = self.factura_memoria.\
                replace('account.invoice', '').replace('(', '').replace(')', '').split(',')
            n = 0
            # noinspection PyUnusedLocal
            for i in factura_memoria_lista:

                if factura_memoria_lista[n] == '':
                    factura_memoria_lista[n] = 0
                else:
                    factura_memoria_lista[n] = int(factura_memoria_lista[n])
                n = n + 1
            numero_facturas_memoria = len(factura_memoria_lista)
            if factura_memoria_lista[numero_facturas_memoria-1] == 0:
                del factura_memoria_lista[numero_facturas_memoria - 1]
                numero_facturas_memoria = len(factura_memoria_lista)
        numero_facturas = len(self.factura_ids)
        if numero_facturas < numero_facturas_memoria:
            for factura_memoria_id in factura_memoria_lista:
                FACTURA = self.env['account.invoice'].search([('id', '=', factura_memoria_id)])
                FACTURA.bool_activo_no_corriente = True
                for factura_id in self.factura_ids:
                    if factura_memoria_id == factura_id.id:
                        FACTURA.bool_activo_no_corriente = False
                vals = {'bool_activo_no_corriente': FACTURA.bool_activo_no_corriente}
                formulario = self.env['account.invoice'].search([('id', '=', FACTURA.id)])
                formulario.write(vals)
            self.factura_memoria = str(self.factura_ids)
        else:
            self.factura_memoria = str(self.factura_ids)
            for factura_id in self.factura_ids:
                factura_id.bool_activo_no_corriente = False
                vals = {'bool_activo_no_corriente': factura_id.bool_activo_no_corriente}
                formulario = self.env['account.invoice'].search([('id', '=', factura_id.id)])
                formulario.write(vals)

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    @api.multi
    def compute_journal_asset(self):
        for rec in self:
            # noinspection PyProtectedMember
            debit = credit = rec.currency_id._convert(rec.value, rec.currency_id, rec.company_id, rec.date)
            if rec.state != 'draft':
                raise UserError("NO SE PUEDE MODIFICAR UN DIARIO MARCADO COMO: (" + rec.state + ')')
            # ----------------------------------------------------
            # CREACION DEL COMENTARIO AL PIE DEL DIARIO
            # SE ESPECIFICA EL ORIGEN DETALLADO DEL ACTIVO
            # SE TOMAN DATOS DE LA FACTURA ORIGEN LINEA POR LINEA
            # ----------------------------------------------------
            comentario = ""
            contador = 0
            for factura_id in self.factura_ids:
                number = factura_id.number
                FACTURAS = self.env['account.invoice'].search([('number', '=', number)])
                for factura in FACTURAS:
                    for line in factura.mapped('invoice_line_ids'):
                        if line.account_id.user_type_id.id == 6:
                            for tax in line.invoice_line_tax_ids:
                                tipo_impuesto = tax.name[0:3]
                                if tipo_impuesto == 'IVA':
                                    # ---------------------------------------------------------------
                                    # IMPRESION EN QWEB DE LINEAS INFORMATIVAS ACTIVOS NO CORRIENTES
                                    # ALGORITMO
                                    # ---------------------------------------------------------------
                                    porcentaje_impuesto = int(tax.name[3:6])
                                    longitud_total = 110
                                    fijas = 60
                                    Fecha_str = str(factura.date_invoice)
                                    Fecha_obj = datetime.strptime(Fecha_str, '%Y-%m-%d').date()
                                    FECHA = Fecha_obj.strftime("%d/%m/%Y")
                                    proveedor = len(factura.partner_id.name)
                                    total = len(str('${:0,.2f}'.format(line.price_subtotal * (1 + porcentaje_impuesto / 100))))
                                    longitud = fijas + proveedor + total
                                    if longitud < longitud_total:
                                        espacios = longitud_total - longitud
                                        PROVEEDOR = factura.partner_id.name
                                        # noinspection PyUnusedLocal
                                        ESPACIOS = " " + "".join(["*" for n in range(1, espacios)])
                                    else:
                                        ESPACIOS = ' ***'
                                        espacios = len(ESPACIOS)
                                        diferencia = longitud - longitud_total + espacios
                                        longitud_nueva_proveedor = proveedor - diferencia
                                        PROVEEDOR = factura.partner_id.name[0:longitud_nueva_proveedor]
                                        # proveedor = len(PROVEEDOR)
                                    contador = contador + 1
                                    NUMERO = factura.number
                                    REFERENCIA = factura.reference
                                    TOTAL = '  ' + str('${:0,.2f}'.format(line.price_subtotal * (1 + porcentaje_impuesto / 100)))
                                    CONTADOR = str('%02i' % int(contador))
                                    comentario = comentario + \
                                                 CONTADOR + ') ' + \
                                                 FECHA + ' | ' + \
                                                 NUMERO + ' | ' + \
                                                 REFERENCIA + ' | ' + \
                                                 PROVEEDOR + ' | ' + \
                                                 ESPACIOS + ' ' + \
                                                 TOTAL + '\n'
            if rec.state == 'draft':
                cuenta_credito_id = rec.cuenta_credito_id.id
                cuenta_debito_id = rec.category_id.account_asset_id.id
                move = {
                        'name': '/',                            # '/' GENERA UN PREFIX TEMPORAL AL FORMULARIO - NORMA DE ODOO
                        'journal_id': 3,                        # 001-001-DIARIO GENERAL
                        'date': rec.date,                       # FECHA DE GENERACION DEL DOCUMENTO
                        'ref': rec.code,                        # REFERENCIA
                        'narration': comentario,                # COMENTARIO DETALLADO DEL ACTIVO

                        'line_ids': [(0, 0, {
                            'name': rec.name,                   # NOMBRE DEL ACTIVO
                            'credit': credit,                   # VALOR MONETARIO DEL HABER
                            'account_id': cuenta_credito_id,    # 1.02.07.06 OTROS ACTIVOS NO CORRIENTES POR DEFECTO
                            'partner_id': {},                   # CAMPO VACIO
                        }), (0, 0, {
                            'name': rec.name,                   # NOMBRE DEL ACTIVO
                            'debit': debit,                     # VALOR MONETARIO DEL DEBE
                            'account_id': cuenta_debito_id,     # CUENTA DECLARADA EN LA GENERACION DEL TIPO DE ACTIVO
                            'partner_id': {},                   # CAMPO VACIO
                        })]
                    }
                if not self.diario_id:
                    # --------------------
                    # CREACION DEL DIARIO
                    # --------------------
                    move_id = self.env['account.move'].create(move)
                    self.diario_id = move_id
                else:
                    # ------------------------
                    # MODIFICACION DEL DIARIO
                    # ------------------------
                    # BORRADO DE LÍNEAS
                    # ------------------
                    self.diario_id.line_ids = [(5, 0, 0), (5, 0, 0)]
                    # -------------------------
                    # ACTUALIZACION DEL DIARIO
                    # -------------------------
                    self.diario_id.update(move)
                    # move_id = self.diario_id
                return

    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # –––––––––––––––––––––––––––––––––––––––––––––––––––––– @api ––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # ------------------------------------------------------------------------------------------------------------------
    #  OOO  OOOO   OOO   OOO  O  OOOO      O   OOOO  O    OOOO  OOOOO  OOOO  OOO  OOOO    O   OOOOO  OOO  OOOO
    # O   O O   O O   O O   O O O         O O  O   O O    O   O O     O     O   O O   O  O O    O   O   O O   O
    # O   O O   O O   O O   O    OOO     O   O OOOO  O    O   O OOO   O     O   O OOOO  O   O   O   O   O OOOO
    # O   O O   O O   O O   O       O    OOOOO O     O    O   O O     O     O   O O  O  OOOOO   O   O   O O  O
    #  OOO  OOOO   OOO   OOO    OOOO     O   O O     O    OOOO  OOOOO  OOOO  OOO  O   O O   O   O    OOO  O   O
    #
    #  OOOO   O   O     O
    # O      O O  O     O
    # O     O   O O     O
    # O     OOOOO O     O
    #  OOOO O   O OOOOO OOOOO
    # ------------------------------------------------------------------------------------------------------------------
    @api.multi
    def compute_validate(self):

        if not self.diario_id.amount:
            # ----------------------
            # FIXME: INICIA INJERTO
            # ---------------------------------------------------------------------------
            # MESSAGE_BOX CODE: USAR PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
            # SOLO PARA @api.multi
            # ---------------------------------------------------------------------------
            title = "ADVERTENCIA: NO SE PUEDE COMPLETAR ESTE PROCESO"
            message = 'NO EXISTE EL ASIENTO CONTABLE DE CREACION DEL ACTIVO. PROCEDA A PRESIONAR EL ' \
                      'BOTON [TABLA_MORTIZACION] Y CONFIRME NUEVAMENTE.'
            view = self.env.ref('l10n_ec_partner.message_box_form')
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
        if self.value == self.diario_id.amount:
            # -----------------------------------------------------------
            # FIXME: INICIA EL CALL - SE LLAMA AL PROCESO NORMAL DE ODOO
            # ---------------------------------------------------------------------------
            # SE MANTIENE LA ESTRUCTURA DEL DECORATOR DE ODOO:
            # tipo:     @api.multi
            # FUNCION:  def validate(self)
            # ORIGEN:   /addons/account_asset/models/account_asset.py
            # CLASS:    AccountAssetAsset(models.Model):
            # ---------------------------------------------------------------------------
            self.validate()
        else:
            # ----------------------
            # FIXME: INICIA INJERTO
            # ---------------------------------------------------------------------------
            # MESSAGE_BOX CODE: USAR PARA MENSAJES INFORMATIVOS QUE NO DETENGAN PROCESOS
            # SOLO PARA @api.multi
            # ---------------------------------------------------------------------------
            title = "ADVERTENCIA: NO SE PUEDE COMPLETAR ESTE PROCESO"
            message = 'EL VALOR NETO DEL ACTIVO ' + str('${:0,.2f}'.format(self.value)) + ' A SER AMORTIZADO O DEPRECIADO' + \
                      ', NO COINCIDE CON EL MONTO TOTAL DEL DIARIO ' + str('${:0,.2f}'.format(self.diario_id.amount)) + \
                      '. PRESIONE EL BOTÓN [TABLA_AMORTIZACION] Y CONFIRME NUEVAMENTE.'
            view = self.env.ref('l10n_ec_partner.message_box_form')
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
    # ------------------------------------------------------------------------------------------------------------------
    #  OOO  OOOO   OOO   OOO  O  OOOO      O   OOOO  O    OOOO  OOOOO  OOOO  OOO  OOOO    O   OOOOO  OOO  OOOO
    # O   O O   O O   O O   O O O         O O  O   O O    O   O O     O     O   O O   O  O O    O   O   O O   O
    # O   O O   O O   O O   O    OOO     O   O OOOO  O    O   O OOO   O     O   O OOOO  O   O   O   O   O OOOO
    # O   O O   O O   O O   O       O    OOOOO O     O    O   O O     O     O   O O  O  OOOOO   O   O   O O  O
    #  OOO  OOOO   OOO   OOO    OOOO     O   O O     O    OOOO  OOOOO  OOOO  OOO  O   O O   O   O    OOO  O   O
    #
    # O  O   O     O OOOOO OOOO  OOOOO
    # O  OO  O     O O     O   O   O
    # O  O O O     O OOO   OOOO    O
    # O  O  OO O   O O     O  O    O
    # O  O   O  OOO  OOOOO O   O   O
    # ------------------------------------------------------------------------------------------------------------------
    @api.multi
    def unlink(self):
        # ----------------------
        # FIXME: INICIA INJERTO
        # --------------------------------------------------------------------
        # RECUPERA A SU CONDICION NORMAL EL ATRIBUTO bool_activo_no_corriente
        # EN LA FACTURA
        # --------------------------------------------------------------------
        for asset in self:
            diario_id = asset.diario_id
            if diario_id.state in ['posted']:
                raise UserError(_('No puede Eliminar un Diario que se encuentra  en estado %s.') % (diario_id.state,))
            else:
                diario_id.unlink()
            for factura_id in asset.factura_ids:
                factura_id.bool_activo_no_corriente = True
                vals = {'bool_activo_no_corriente': factura_id.bool_activo_no_corriente}
                formulario = asset.env['account.invoice'].search([('id', '=', factura_id.id)])
                formulario.write(vals)
        # ------------------------------
        # FIXME: PROCESO NORMAL DE ODOO
        # ---------------------------------------------------------------------------
        # SE MANTIENE LA ESTRUCTURA DEL DECORATOR DE ODOO:
        # tipo:     @api.multi
        # FUNCION:  def unlink(self)
        # ORIGEN:   /addons/account_asset/models/account_asset.py
        # CLASS:    AccountAssetAsset(models.Model):
        # ---------------------------------------------------------------------------
        for asset in self:
            if asset.state in ['open', 'close']:
                raise UserError(_('You cannot delete a document that is in %s state.') % (asset.state,))
            for depreciation_line in asset.depreciation_line_ids:
                if depreciation_line.move_id:
                    raise UserError(_('You cannot delete a document that contains posted entries.'))
        return super(AccountAssetAsset, self).unlink()
