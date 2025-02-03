from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict
import ast
import logging

_logger = logging.getLogger(__name__)
class Account_payment_methods(models.Model):
    
    _inherit = 'account.payment.multiplemethods'

    currency_id = fields.Many2one(
        'res.currency',
        string='Divisa',
        compute ='_compute_currency_id',
        required = True,
        store=True,
    )
    
    exchange_rate = fields.Float('Exchange rate',compute = '_compute_exchange_rate')
    
    other_currency = fields.Boolean('Other currency',compute ='_compute_other_currency',default = False, readonly = True)
    manual_company_currency = fields.Boolean(
        string="Ajuste manual de cambio",
        default=False,
        help="Enable manual editing of Amount on Company Currency and automatic recalculation of Exchange Rate."
)
    payment_total_ars = fields.Monetary(
        compute='_compute_payment_total',
        string='Total a pagar',
        currency_field='company_currency_id'
    )
    payment_total_usd = fields.Monetary(
        compute='_compute_payment_total_usd',
        string='Total a pagar (USD)',
        currency_field='currency_id'
    )
    payment_difference = fields.Monetary(
        compute='_compute_payment_difference',
        readonly=True,
        string="Diferencia",
        currency_field='company_currency_id',
        help="Difference between selected debt (or to pay amount) and "
        "payments amount"
    )
    payment_difference_usd = fields.Monetary(
        compute='_compute_payment_difference_usd',
        readonly=True,
        string="Diferencia (USD)",
        currency_field='currency_id',
        help="Difference between selected debt (or to pay amount) and "
        "payments amount"
    )

    selected_debt_usd = fields.Monetary(
        # string='To Pay lines Amount',
        string='Deuda seleccionada (USD)',
        compute='_compute_selected_debt_usd',
        currency_field='currency_id',
    )
    unreconciled_amount_usd = fields.Monetary(
        string='Ajuste / Avance',
        currency_field='currency_id',
    )
    to_pay_amount_usd = fields.Monetary(
        compute='_compute_to_pay_amount_usd',
        inverse='_inverse_to_pay_amount_usd',
        string='Monto a pagar',
        # string='Total To Pay Amount',
        readonly=True,
        currency_field='currency_id',
    )

    @api.depends('to_pay_move_line_ids')
    def _compute_currency_id(self):
        for rec in self:
            for line in rec.to_pay_move_line_ids:
                rec.currency_id = line.currency_id
        return

    @api.depends('to_pay_move_line_ids', 'to_pay_move_line_ids.amount_residual')
    def _compute_selected_debt_usd(self):
        for rec in self:
            # factor = 1
            rec.selected_debt_usd = sum(rec.to_pay_move_line_ids._origin.mapped('amount_residual_currency')) * (-1.0 if rec.partner_type == 'supplier' else 1.0)
            # TODO error en la creacion de un payment desde el menu?
            # if rec.payment_type == 'outbound' and rec.partner_type == 'customer' or \
            #         rec.payment_type == 'inbound' and rec.partner_type == 'supplier':
            #     factor = -1
            # rec.selected_debt = sum(rec.to_pay_move_line_ids._origin.mapped('amount_residual')) * factor
    
    @api.depends('to_pay_payment_ids','withholding_line_ids')
    def _compute_payment_total_usd(self):
        """ new field similar to amount_company_currency_signed but:
        1. is positive for payments to suppliers
        2. we use the new field amount_company_currency instead of amount_total_signed, because amount_total_signed is
        computed only after saving
        We use l10n_ar prefix because this is a pseudo backport of future l10n_ar_withholding module """
        for rec in self:
            rec.payment_total_usd = 0
            for payment in rec.to_pay_payment_ids:
                if payment.payment_type == 'outbound' and payment.partner_type == 'customer' or \
                        payment.payment_type == 'inbound' and payment.partner_type == 'supplier':
                    rec.payment_total_usd += -payment.amount
                else:
                    rec.payment_total_usd += payment.amount

    @api.depends('payment_total_usd', 'to_pay_amount_usd')
    def _compute_payment_difference_usd(self):
        for rec in self:
            rec.payment_difference_usd = rec._get_payment_difference_usd() - sum(self.withholding_line_ids.mapped('amount'))             
    def _get_payment_difference_usd(self):
        return self.to_pay_amount_usd - self.payment_total_usd

    @api.depends(
        'selected_debt_usd', 'unreconciled_amount_usd')
    def _compute_to_pay_amount_usd(self):
        for rec in self:
            rec.to_pay_amount_usd = rec.selected_debt_usd + rec.unreconciled_amount_usd
    
    @api.onchange('to_pay_amount_usd')
    def _inverse_to_pay_amount_usd(self):
        for rec in self:
            rec.unreconciled_amount_usd = rec.to_pay_amount_usd - rec.selected_debt_usd
    
    @api.depends('currency_id')
    def _compute_other_currency(self):
        _logger.info('Compute other currency')
        for rec in self:
            if rec.currency_id == rec.company_currency_id:
                rec.other_currency = False
            else:
                rec.other_currency = True
            _logger.info(f"Other currency: {rec.other_currency}")

    @api.depends('other_currency', 'to_pay_move_line_ids')
    def _compute_exchange_rate(self):
        for rec in self:
            _logger.info(f"Other currency exchange: {rec.other_currency}")
            if rec.other_currency:
                if rec.manual_company_currency:
                    if rec.other_currency:
                        rec.exchange_rate = rec.payment_total and (
                            rec.amount_company_currency / rec.payment_total) or 0.0
                    else:
                        rec.exchange_rate = False
                    continue
                if rec.state != 'posted' and len(rec.to_pay_move_line_ids) > 0:
                    first_move_line = rec.to_pay_move_line_ids[0]
                    if first_move_line.move_id.l10n_ar_currency_rate:
                        rec.exchange_rate = first_move_line.move_id.l10n_ar_currency_rate
                        _logger.info(rec.exchange_rate)
                    else:
                        rec.exchange_rate = rec.amount and (
                            rec.amount_company_currency / rec.payment_total) or 0.0
                
                else:
                    if rec.matched_move_line_ids:
                        first_move_line = rec.matched_move_line_ids[0] if rec.matched_move_line_ids else False
                        if first_move_line.move_id.l10n_ar_currency_rate:
                            rec.exchange_rate = first_move_line.move_id.l10n_ar_currency_rate
                            _logger.info(rec.exchange_rate)
                        else:
                            rec.exchange_rate = rec.payment_total and (
                                rec.amount_company_currency / rec.payment_total) or 0.0
                    else:
                        rec.exchange_rate = rec.payment_total and (
                                rec.amount_company_currency / rec.payment_total) or 0.0
            else:
                rec.exchange_rate = 0.0

    def add_payment(self):
        if not self.is_advanced_payment:
            self.ensure_one()
        # Crear el asistente y llenar line_ids con to_pay_move_line_ids
        payment_register = self.env['custom.account.payment.register'].create({
            'line_ids': [(6, 0, self.to_pay_move_line_ids.ids)],
            'multiple_payment_id': self.id,# Aquí asignamos el ID del primer modelo
            'amount_received' : self.payment_difference,
            'journal_id':self.last_journal_used.id,
            'payment_method_line_id':self.last_payment_method_line_id.id,
            'is_advanced_payment':self.is_advanced_payment,
            'company_id':self.company_id.id,
            'partner_type':self.partner_type,
            'partner_id':self.partner_id.id,
            'currency_id':self.currency_id.id,
            'payment_type':self.payment_type,
            'exchange_rate':self.exchange_rate
        })
    
        # Devolver la acción para abrir el asistente en una ventana modal
        return {
            'name': 'Registrar Pago',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.account.payment.register',
            'view_mode': 'form',
            'view_id': self.env.ref('account-payment-group.view_custom_account_payment_register_form').id,  # Reemplaza con el ID de la vista del asistente
            'target': 'new',
            'res_id': payment_register.id,
            'context': {
                'default_multiple_payment_id': self.id,
                'default_amount_received': self.payment_difference,
                **self.env.context,
            },
        }

   