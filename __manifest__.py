# -*- coding: utf-8 -*-
{
    'name': "Account Payment Auto Exchange rate",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "OutsourceArg",
    'website': "https://www.oursourcearg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Payments',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['account_payment_pro','account-payment-group'],
    'data':['views/account_payment_views.xml',
            'views/account_payment_group.xml',
            'views/account_move_views.xml',
           ]
    # only loaded in demonstration mode
}