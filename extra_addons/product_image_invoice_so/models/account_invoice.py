# -*- coding: utf-8 -*-
from openerp import models, fields

class account_invoice(models.Model):
    _inherit = 'account.invoice'

    print_image = fields.Boolean('Print Image', help="""If invoice, you can see
                    the product image in report of Invoice""")
    image_sizes = fields.Selection([('image', 'Big sized Image'),
                                    ('image_medium', 'Medium Sized Image'),
                                    ('image_small', 'Small Sized Image')],
                                   'Image Sizes',
                                   default="image_small",
                                   help="Image size to be displayed in report")

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    image_small = fields.Binary('Imagen del Producto',
                                related='product_id.image_small')
