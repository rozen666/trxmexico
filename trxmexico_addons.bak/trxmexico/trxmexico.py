 
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#   
#    Code: Creaty by: Ing. Luis J. Ortega 12/02/2018
#
##############################################################################
import sys 
reload(sys)
sys.setdefaultencoding('utf-8')
from openerp import SUPERUSER_ID
from openerp import models, fields, api, tools
from openerp.osv import osv
from openerp.exceptions import Warning
from datetime import time, datetime, date, timedelta
import os
import xlrd 
from xlrd import open_workbook
import base64
import time
import calendar
#from stdnum.mx.rfc import (validate,InvalidComponent,InvalidFormat,InvalidLength,InvalidChecksum)

TRX_DESCUENTO_COTIZACION = [
            ('1','Descuento Total'),
            ('2','Descuento por Producto'),
            ('0','Sin Descuento'),
            ]

TRX_STATUS_PARTNER = [
            ('ACTIVO','ACTIVO'),
            ('NO_ACTIVO','NO ACTIVO'),
            ]

class res_users(models.Model):
    _name="res.users"
    _inherit="res.users"
    
    #Campos TRXMexico res_partner

res_users()

class res_partner(models.Model):
    _name="res.partner"
    _inherit="res.partner"
    
    #Campos TRXMexico res_partner
    domicilio_partner = fields.Text(string='Domicilio')
    clave_partner = fields.Char(string='Clave de Usuario')
    rfc_partner = fields.Char(string='RFC')
    status_partner = fields.Selection(TRX_STATUS_PARTNER,string='Estatus')

    # Boton para validar que el RFC sea verdadero
   # @api.multi
   # def button_validate_rfc(self):
   # 	# Se revisa que no sea un RFC generico para persona moral/fisica
   # 	if self.rfc_partner == "XEXX010101000" or self.rfc_partner == "XAXX010101000":
   # 		return True
   # 	else:
   # 		# Se comprueba que sea valido
   # 		try:
   # 			retorno = validate( self.rfc_partner, validate_check_digits=True)
   ## 			return True
   # 		except:
   # 			# De lo contrario dispara Alert
   # 			raise osv.except_osv(("¡Error!"),('El RFC no es Valido, Favor de verificar'))

res_partner()

class product_product(models.Model):
    _name="product.product"
    _inherit="product.product"
    
    #Campos TRXMexico product_product
    price_sell_mxn = fields.Float(string='Precio de Venta (MXN)', index=True)

product_product()

class account_invoice(models.Model):
	_name="account.invoice"
	_inherit="account.invoice"

	@api.model
	def _default_date(self):
		res = fields.Date.today()
		return res

	#Campos TRXMexico account_invoice
	referencia_cotizacion = fields.Char(string='Código/Folio de Cotización')
	name_vendedor = fields.Many2one('res.users',string='Nombre del Vendedor', index=True)
	descuento_habilitar = fields.Selection(TRX_DESCUENTO_COTIZACION,string='Descuento Total')
	descuento = fields.Char(string='Descuento Total %', size=4)
	des_subtotal = fields.Float(string='Descuento ', size=10)
	invoice_id = fields.Many2many('trxmexico.condiciones.pago', 'account_invoice_rel', 'account_id','invoice_id', 'Condiciones de Pago', copy=False)
	invoice_id_entrega = fields.Many2many('trxmexico.condiciones.entrega', 'account_invoice_rel_ent', 'account_id','invoice_id_entrega', 'Condiciones de Pago', copy=False)
	invoice_id_general = fields.Many2many('trxmexico.condiciones.generales', 'account_invoice_rel_gral', 'account_id','invoice_id_general', 'Condiciones de Pago', copy=False)
	subtotal_con_desc = fields.Float(string='Sub-Total con Descuento', size=10)
	total_con_desc = fields.Float(string='Total con Descuento', size=10)
	fecha_cotizacion = fields.Date(string='Fecha de Cotización', default=_default_date)

	# Se modifica el create para poder crear un Codigo irrepetible por cotización
	# [TODO]---Se pude modificar por 'ir.sequence'
	def create(self, cr, uid, values, context=None):
		# Se realiza busqueda para revisar todos los coodigos
		records = self.pool.get('account.invoice').search(cr, SUPERUSER_ID, [('referencia_cotizacion','!=',False)], context=context)
		# Si no hay codigos, se inicia en 1 el conteo
		if records == []:
			new_subfijo = 1
		# Si encuentra trae el ultimo de todos mayor de todos y le aumenta uno
		else:
			segunda_busqueda = self.browse(cr,uid, records)
			lista_subfijos = []
			for elemento in segunda_busqueda:
				matri = elemento.referencia_cotizacion
				subfix_temp = int(matri[9:])
				lista_subfijos.append(subfix_temp)
			maximo_ele = max(lista_subfijos)
			new_subfijo = maximo_ele + 1

		# Crea el codígo con el subfijo y la nomenclatura
		anio = str(date.today().year)
		code = 'CTZ'+'-'+anio+'-'+str(new_subfijo).zfill(5)
		values['referencia_cotizacion'] = code

		create = super(account_invoice, self).create(cr, uid, values, context=context)
		return create

		# Boton que permite actualizar los impuestos segun el tipo de Descuento (field->descuento_habilitar)
	@api.multi
	def button_reset_taxes_trx(self):
		account_invoice_tax = self.env['account.invoice.tax']
		ctx = dict(self._context)
		for invoice in self:
			# Borramos el impiuesto anterior
			self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
			self.invalidate_cache()
			partner = invoice.partner_id
			if partner.lang:
				ctx['lang'] = partner.lang

			# Creamos funcion para opción sin descuento
			if invoice.descuento_habilitar =='0' or invoice.descuento_habilitar ==False:
				# Se crea una busqueda para cada concepto realcionado al Invoice
				for taxed in self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)]):
					if taxed.descuento:
						raise osv.except_osv('Descuento no permitido en Concepto', 'Se ha seleccionado un descuento para el producto %s, modifique el concepto e intente de nuevo.'%taxed.product_id.name)
					# Se obtiene el precio original de cada producto y se asigna a cada concepto
					price_subtotal = float(taxed.product_id.lst_price)
					taxed.write({'price_unit': price_subtotal})

					# Si se selecionan más de 2 impuestos por concepto se dispara un Warning
					if len(taxed.invoice_line_tax_id)>=2:
						raise osv.except_osv('Multiple Impuesto por Producto', 'Se ha seleccionado más de un impuesto para el producto %s, modifique el concepto e intente de nuevo, Por Favor.'%taxed.product_id.name)

					# Se crea un arreglo con las varibles para el impuesto
					taxe = {
						'tax_amount': float(taxed.price_subtotal) * float(taxed.invoice_line_tax_id.amount),
						'name': 'IVA(16%) VENTAS',
						'sequence': 1,
						'invoice_id' : taxed.invoice_id.id,
						'manual': False,
						'base_amount':float(taxed.product_id.lst_price),
						'base_code_id': taxed.invoice_line_tax_id.base_code_id.id,
						'tax_code_id': taxed.invoice_line_tax_id.tax_code_id.id,
						'amount': float(taxed.price_subtotal) * float(taxed.invoice_line_tax_id.amount),
						'base': float(taxed.product_id.lst_price),
						'account_analytic_id': False,
						'account_id': 260
					}
					# Se crea el impuesto con el arreglo 'taxe'
					account_invoice_tax.create(taxe)
			
			# Creamos funcion para opción Descuento Total
			if invoice.descuento_habilitar =='1':
				subtotal = 0
				taxe_total = 0
				# Se dispara Warning si no hay cantidad den el descuento
				if invoice.descuento == False:
					raise Warning("No se ingresado ningun Descuento para el total de la cotización")

				# Se hace una busqueda y revisa que no haya conceptos con descuento
				for taxed in self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)]):
					if taxed.descuento:
						# Si encuentra conceptos con descuentos dispara Warning
						raise osv.except_osv('Descuento en Concepto','La opción seleccinada no permite realizar el descuento %s% para el producto %s'%(taxed.descuento,taxed.product_id.name))
					
					# Se crea un arreglo con las varibles para el impuesto
					taxe = {
						'tax_amount': float(taxed.price_subtotal) * float(taxed.invoice_line_tax_id.amount),
						'name': 'IVA(16%) VENTAS',
						'sequence': 1,
						'invoice_id' : taxed.invoice_id.id,
						'manual': False,
						'base_amount':float(taxed.product_id.lst_price),
						'base_code_id': taxed.invoice_line_tax_id.base_code_id.id,
						'tax_code_id': taxed.invoice_line_tax_id.tax_code_id.id,
						'amount': float(taxed.price_subtotal) * float(taxed.invoice_line_tax_id.amount),
						'base': float(taxed.product_id.lst_price),
						'account_analytic_id': False,
						'account_id': 260
					}
					# Se crea el impuesto con el arreglo 'taxe'
					account_invoice_tax.create(taxe)
					taxe_total = taxe_total + taxe['tax_amount']
					price_subtotal = float(taxed.product_id.lst_price)
					taxed.write({'price_unit': price_subtotal})
					subtotal = subtotal + price_subtotal

					# Si se selecionan más de 2 impuestos por concepto se dispara un Warning
					if len(taxed.invoice_line_tax_id)>=2:
						raise osv.except_osv('Multiple Impuesto por Producto', 'Se ha seleccionado más de un impuesto para el producto %s, modifique el concepto e intente de nuevo, Por Favor.'%taxed.product_id.name)
				desc_total = float(subtotal) * float(float(invoice.descuento)/100)
				subtotal = float(subtotal) - float(desc_total)
				total_des = float(subtotal) + float(taxe_total)
				# Asignamos el valor que se descuenta a la variable des_subtotal
				invoice.write({'des_subtotal': desc_total,'subtotal_con_desc' : subtotal,'total_con_desc':total_des})

			# Creamos funcion para opción con descuento por concepto
			if invoice.descuento_habilitar =='2':
				# Se crea una busqueda para cada concepto realcionado al Invoice
				for taxed in self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)]):
					# Si se coloca un descuento fuera de rango (0-100) se dispara Warning
					if int(taxed.descuento) > 100 or int(taxed.descuento) < 0:
						raise Warning("No se pueden hacer descuentos mayores a 100% ni menores del %0")

					# Si hay conceptos con descuento se realiza la operación para obtner el precio con el descuento de lo contrario se asigna el valor original de cada producto
					if taxed.descuento != 0:
						price_subtotal = float(taxed.product_id.lst_price) * float(float(taxed.descuento)/100)
						price_subtotal = float(taxed.product_id.lst_price) - float(price_subtotal)
					else:
						price_subtotal = float(taxed.product_id.lst_price)
					taxed.write({'price_unit': price_subtotal})

					# Si se selecionan más de 2 impuestos por concepto se dispara un Warning
					if len(taxed.invoice_line_tax_id)>=2:
						raise osv.except_osv('Multiple Impuesto por Producto', 'Se ha seleccionado más de un impuesto para el producto %s, modifique el concepto e intente de nuevo, Por Favor.'%taxed.product_id.name)
					# Se crea un arreglo con las varibles para el impuesto
					taxe = {
						'tax_amount': float(taxed.price_subtotal) * float(taxed.invoice_line_tax_id.amount),
						'name': 'IVA(16%) VENTAS',
						'sequence': 1,
						'invoice_id' : taxed.invoice_id.id,
						'manual': False,
						'base_amount':price_subtotal,
						'base_code_id': taxed.invoice_line_tax_id.base_code_id.id,
						'tax_code_id': taxed.invoice_line_tax_id.tax_code_id.id,
						'amount': float(taxed.price_subtotal) * float(taxed.invoice_line_tax_id.amount),
						'base': price_subtotal,
						'account_analytic_id': False,
						'account_id': 260
					}
					# Se crea el impuesto con el arreglo 'taxe'
					account_invoice_tax.create(taxe)

		# Se re-escribe sobre el Invoice que se esta trabajando
		return self.with_context(ctx).write({'invoice_line': []})


account_invoice()

class account_invoice_line(models.Model):
	_name="account.invoice.line"
	_inherit="account.invoice.line"


	#Campos TRXMexico account_invoice_line
	price_sell_mxn = fields.Float(string='Precio MXN', index=True)
	descuento = fields.Char(string='Descuento %', size=4)


account_invoice_line()

class trxmexico_condiciones_pago(models.Model):
	_name="trxmexico.condiciones.pago"
	_rec_name = 'details'

	#Campos TRXMexico trxmexico_condiciones_pago
	name = fields.Char(string='Condiciones de Pago')
	details = fields.Text(string='Condiciones de Pago')
	account_id = fields.Many2many('account.invoice', 'account_invoice_rel', 'invoice_id','account_id', 'Condiciones de Pago', copy=False)


trxmexico_condiciones_pago()

class trxmexico_condiciones_entrega(models.Model):
	_name="trxmexico.condiciones.entrega"
	_rec_name = 'details'

	#Campos TRXMexico trxmexico_condiciones_entrega
	name = fields.Char(string='Condiciones de Pago')
	details = fields.Text(string='Condiciones de Pago')
	account_id = fields.Many2many('account.invoice', 'account_invoice_rel', 'invoice_id_entrega','account_id', 'Condiciones de Entrega', copy=False)


trxmexico_condiciones_entrega()

class trxmexico_condiciones_generales(models.Model):
	_name="trxmexico.condiciones.generales"
	_rec_name = 'details'

	#Campos TRXMexico trxmexico_condiciones_generales
	name = fields.Char(string='Condiciones de Pago')
	details = fields.Text(string='Condiciones de Pago')
	account_id = fields.Many2many('account.invoice', 'account_invoice_rel', 'invoice_id_general','account_id', 'Condiciones de Generales', copy=False)


trxmexico_condiciones_generales()

class trxmexico_change_monetary(models.Model):
	_name='trxmexico.change.monetary'

	# Compute para sacar el tipo de moneda en pesos siempre
	@api.model
	def _default_curreny(self):
		currency_id = self.env['res.currency'].search([('name', '=', "MXN")])
		return currency_id[0]

	# Compute para sacar el costo del dolar anteriror
	@api.model
	def _default_price_before(self):
		price = 0.0
		prices_id = self.env['trxmexico.change.monetary'].search([('id', '=', 1)])
		if prices_id:
			price = prices_id.price_dolar

		return price
	#Campos TRXMexico trxmexico_change_monetary
	price_dolar = fields.Float(string='Pesos')
	price_before = fields.Float(string='Costo anterior', default=_default_price_before)
	currency_id = fields.Many2one('res.currency',string='Tip de moneda', default=_default_curreny)

	# Funcion que permite sobreescribir el mismo regitro y elimina los registros basura
	@api.multi
	def button_change_money(self):
		# Se busca el primer registro y se asigna el valor del dolar
		prices_id = self.env['trxmexico.change.monetary'].search([('id', '=', 1)])
		prices_id.write({'price_dolar':self.price_dolar})
		# Los registros sobrantes existentes son eliminados
		for price_delete in self.env['trxmexico.change.monetary'].search([('id', '>', 1)]):
			self.env['trxmexico.change.monetary'].search([('id','=', price_delete.id)]).unlink()



trxmexico_change_monetary()







