# -*- coding: utf-8 -*-
{
    'name': "TRXmexico",
    'summary': """
        Sistema de Cotización para TRXMexico""",

    'description': """
        Aplicación de cotizaciónes para TRXMexico
    """,

    'author': "BPMTech",
    'category': 'trxexico',
    'version': '1.0',   
    # any module necessary for this one to work correctly
    'depends': ['base','stock', 'mail','website','account'],
    # always loaded
    'data': [
        'view/trxmexico_view.xml',
        'data/trxmexico_condiciones.xml',
        'data/email_templates.xml',
        'security/trx_security.xml',
        'security/menu_hide_view.xml',
        'security/ir.model.access.csv',

    ],
    
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}


