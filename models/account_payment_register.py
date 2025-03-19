from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict
from odoo.tools import frozendict
import pprint


class CustomAccountPaymentRegister(models.TransientModel):
    _inherit = 'custom.account.payment.register'

    exchange_rate = fields.Float('Exchange_rate')

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.journal_id.currency_id or wizard.multiple_payment_id.currency_id.id or wizard.company_id.currency_id

    def _create_payment_vals_from_wizard(self):
            payment_vals = {
                'date': self.payment_date,
                'amount': self.amount,
                'payment_type': self.payment_type,
                'partner_type': self.partner_type,
                'journal_id': self.journal_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'partner_id': self.partner_id.id,
                'partner_bank_id': self.partner_bank_id.id,
                'payment_method_line_id': self.payment_method_line_id.id,
                #'destination_account_id': self.line_ids[0].account_id.id,
                'write_off_line_vals': [],
                'l10n_latam_check_number':self.l10n_latam_check_number,
                'l10n_latam_check_payment_date':self.l10n_latam_check_payment_date,
                'l10n_latam_check_id':self.l10n_latam_check_id.id,
                'multiple_payment_id':self.multiple_payment_id.id,
                'amount_company_currency':self.amount * self.exchange_rate,
                'manual_company_currency':True
            }
            return payment_vals
