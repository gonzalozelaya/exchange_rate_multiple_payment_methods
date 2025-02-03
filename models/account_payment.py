from odoo import api, fields, models, _, Command, SUPERUSER_ID, modules, tools
from odoo.exceptions import UserError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.payment"

    amount_company_currency = fields.Monetary(
        string='Amount on Company Currency',
        compute='_compute_amount_company_currency',
        inverse='_inverse_amount_company_currency',  # Método inverso
        currency_field='company_currency_id',
    )
    manual_company_currency = fields.Boolean(
        string="Ajuste manual de cambio",
        default=False,
        help="Enable manual editing of Amount on Company Currency and automatic recalculation of Exchange Rate."
)
    @api.depends('amount', 'other_currency', 'to_pay_move_line_ids')
    def _compute_exchange_rate(self):
        for rec in self:
            if rec.other_currency:
                if rec.manual_company_currency:
                    if rec.other_currency:
                        rec.exchange_rate = rec.amount and (
                            rec.amount_company_currency / rec.amount) or 0.0
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
                            rec.amount_company_currency / rec.amount) or 0.0
                
                else:
                    if rec.matched_move_line_ids:
                        first_move_line = rec.matched_move_line_ids[0] if rec.matched_move_line_ids else False
                        if first_move_line.move_id.l10n_ar_currency_rate:
                            rec.exchange_rate = first_move_line.move_id.l10n_ar_currency_rate
                            _logger.info(rec.exchange_rate)
                        else:
                            rec.exchange_rate = rec.amount and (
                                rec.amount_company_currency / rec.amount) or 0.0
                    else:
                        rec.exchange_rate = rec.amount and (
                                rec.amount_company_currency / rec.amount) or 0.0
            else:
                rec.exchange_rate = 0.0

    
    @api.depends('amount', 'other_currency', 'force_amount_company_currency','exchange_rate')
    def _compute_amount_company_currency(self):
        """
        * Si las monedas son iguales devuelve 1
        * si no, si hay force_amount_company_currency, devuelve ese valor
        * sino, devuelve el amount convertido a la moneda de la cia
        """
        for rec in self:
            if rec.manual_company_currency:
                if not rec.other_currency:
                    amount_company_currency = rec.amount
                elif rec.force_amount_company_currency:
                    amount_company_currency = rec.force_amount_company_currency
                else:
                    amount_company_currency = rec.currency_id._convert(
                        rec.amount, rec.company_id.currency_id,
                        rec.company_id, rec.date)
                rec.amount_company_currency = amount_company_currency
                continue
            amount_company_currency = rec.amount
            if not rec.other_currency:
                amount_company_currency = rec.amount
            else:
                amount_company_currency = rec.amount * rec.exchange_rate
            rec.amount_company_currency = amount_company_currency
            
    #def _inverse_amount_company_currency(self):
     #   for rec in self:
      #      if rec.amount and rec.other_currency:
       #         rec.exchange_rate = rec.amount_company_currency / rec.amount
        #        _logger.info(f"Exchange rate updated from manual company currency: {rec.exchange_rate}")
    
    @api.depends('amount_company_currency','exchange_rate')
    def _compute_amount_from_dollar(self):
        for rec in self:
            rec.amount = rec.amount_company_currency * rec.exchange_rate