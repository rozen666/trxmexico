 
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
#    Code Create by: Ing. Luis J. Ortega 12/02/2018
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
from openerp import _
import os
import xlrd 
from xlrd import open_workbook
import base64
import time
import calendar
from stdnum.mx.rfc import (validate,InvalidComponent,InvalidFormat,InvalidLength,InvalidChecksum)
from parse import cargar_MA,cargar_Productos
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

ODOO_HOME = "/opt/odoo/"
# ODOO_HOME = "/opt/trxmexico/odoo"

TRX_DESCUENTO_COTIZACION = [
            ('1','Descuento Total'),
            ('2','Descuento por Producto'),
            ('0','Sin Descuento'),
            ]

TRX_SELECCION_CONDICION = [
            ('1','Condiciones de Pago'),
            ('2','Condiciones de Entrega'),
            ('3','Condiciones Generales'),
            ]

TRX_STATUS_PARTNER = [
            ('ACTIVO','ACTIVO'),
            ('NO_ACTIVO','NO ACTIVO'),
            ]

TRX_OPTION_CONDICION = [
            ('1','Agregar'),
            ('2','Eliminar'),
            ]

TRX_OPTION_MONEY = [
            ('1','Dolares'),
            ('2','Pesos'),
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
    @api.multi
    def button_validate_rfc(self):
    	# Se revisa que no sea un RFC generico para persona moral/fisica
    	if self.rfc_partner == "XEXX010101000" or self.rfc_partner == "XAXX010101000":
    		return True
    	else:
    		# Se comprueba que sea valido
    		try:
    			retorno = validate( self.rfc_partner, validate_check_digits=True)
    			return True
    		except:
    			# De lo contrario dispara Alert
    			raise osv.except_osv(("¡Error!"),('El RFC no es Valido, Favor de verificar'))

    # Función para la creación de un repositorio por cliente
    def attachment_doc_project(self, cr, uid, ids, context):

        # Obtenemos a que modelo pertnece
        project_id = self.pool.get('res.partner').browse(cr, uid, ids, context)
        # Creamos un domain unico por registro
        domain = [('res_model', '=', "res.partner"),('res_id','=',project_id.id)]
        res_id = ids and ids[0] or False
        # retornamos los valores para la creación del repositorio
        return {
            'name': _('Cotizaciones'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d, 'default_id_crm_lead': '%s'}" % (self._name, res_id, ids[0]),
            'help': '<p class="oe_view_nocontent_create">Agregar Cotización</p>'
            }

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

	# Defaults para llendo de Fecha, vendedor y todas las condiciones
	@api.model
	def _default_date(self):
		res = fields.Date.today()
		return res

	@api.model
	def _default_user(self):
		res = self.env.user.id
		return res

	@api.model
	def _default_conditions_pago(self):
		return self.env['trxmexico.condiciones.pago'].search([])

	@api.model
	def _default_conditions_entrega(self):
		return self.env['trxmexico.condiciones.entrega'].search([])

	@api.model
	def _default_conditions_general(self):
		return self.env['trxmexico.condiciones.generales'].search([])

	# Compute que revisa el en que tipo de cotización se encuentra, si es False hace las operaciones a base de los DLLS 
	# Si es True , realiza todo en base a MXN
	@api.one
	@api.depends('invoice_line.price_subtotal', 'tax_line.amount')
	def _compute_amount(self):
		if self.type_cotizacion == False:				
			if self.check_envio:
				self.subtotal_con_desc = sum(line.price_subtotal for line in self.invoice_line) + self.costo_envio - float(self.des_subtotal)
			else:
				self.subtotal_con_desc = sum(line.price_subtotal for line in self.invoice_line) - float(self.des_subtotal)
			self.amount_tax = sum(line.amount for line in self.tax_line)
			self.total_con_desc = self.subtotal_con_desc + self.amount_tax
			self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
			dolar_id = self.env['trxmexico.change.monetary'].search([('id', '=', 1)])
			mxn = (self.subtotal_con_desc + self.amount_tax) * float(dolar_id.price_dolar)
			self.amount_tax_mxn =  mxn
		else:
			if self.check_envio:
				self.subtotal_con_desc = sum(line.amount_mxn for line in self.invoice_line) + self.costo_envio - float(self.des_subtotal)
			else:
				self.subtotal_con_desc = sum(line.amount_mxn for line in self.invoice_line) - float(self.des_subtotal)
			self.amount_tax = sum(line.amount for line in self.tax_line)
			self.total_con_desc = self.subtotal_con_desc + self.amount_tax
			self.amount_untaxed = sum(line.amount_mxn for line in self.invoice_line)
			dolar_id = self.env['trxmexico.change.monetary'].search([('id', '=', 1)])
			mxn = (self.subtotal_con_desc + self.amount_tax)
			self.amount_tax_mxn =  mxn


	#Campos TRXMexico account_invoice
	referencia_cotizacion = fields.Char(string='Código/Folio de Cotización')
	name_vendedor = fields.Many2one('res.users',string='Nombre del Vendedor', index=True, default=_default_user)
	descuento_habilitar = fields.Selection(TRX_DESCUENTO_COTIZACION,string='Descuento Total', default='0')
	descuento = fields.Char(string='Descuento Total %', size=4)
	des_subtotal = fields.Float(string='Descuento ', size=10, default=0.0)
	invoice_id = fields.Many2many('trxmexico.condiciones.pago', 'account_invoice_rel', 'account_id','invoice_id', 'Condiciones de Pago', copy=False, default=_default_conditions_pago)
	invoice_id_entrega = fields.Many2many('trxmexico.condiciones.entrega', 'account_invoice_rel_ent', 'account_id','invoice_id_entrega', 'Condiciones de Pago', copy=False, default=_default_conditions_entrega)
	invoice_id_general = fields.Many2many('trxmexico.condiciones.generales', 'account_invoice_rel_gral', 'account_id','invoice_id_general', 'Condiciones de Pago', copy=False, default=_default_conditions_general)
	subtotal_con_desc = fields.Float(string='Sub-Total con Descuento', size=10, compute='_compute_amount', store=True)
	total_con_desc = fields.Float(string='Total ', size=10, compute='_compute_amount', store=True)
	fecha_cotizacion = fields.Date(string='Fecha de Cotización', default=_default_date)
	check_envio = fields.Boolean(string='Cotización con Envio')
	costo_envio = fields.Float(string='Costo Envio')
	amount_tax_mxn = fields.Float(string='Total MXN',compute='_compute_amount')
	type_cotizacion = fields.Boolean(string='Dolar/MXN')

	# Se modifica el create para poder crear un Codigo irrepetible por cotización
	# [TODO]---Se pude modificar por 'ir.sequence'
	@api.model
	def create(self,values):
		if 'in_context' in self._context:
			values['type_cotizacion'] = True

		records = self.search([("referencia_cotizacion","!=",False)])
		if len(records)==0:
			new_subfijo =1

		else:
			lista_subfijos = []
			for elemento in records:
				matri = elemento.referencia_cotizacion
				subfix_temp = int(matri[9:])
				lista_subfijos.append(subfix_temp)
			maximo_ele = max(lista_subfijos)
			new_subfijo = maximo_ele + 1

		# Crea el codígo con el subfijo y la nomenclatura
		anio = str(date.today().year)
		code = 'CTZ'+'-'+anio+'-'+str(new_subfijo).zfill(5)
		values['referencia_cotizacion'] = code
		self.button_reset_taxes_trx()
		rec = super(account_invoice, self).create(values)

		return rec

		# Boton que permite actualizar los impuestos segun el tipo de Descuento (field->descuento_habilitar)
	@api.onchange('invoice_id','invoice_id_entrega','invoice_id_general')
	def _onchange_condiciones(self):
		comments=''
		comments1 =''
		comments12 =''
		comments13 =''
		for c_pago in  self.invoice_id:
			con_pago = self.env['trxmexico.condiciones.pago'].search([('id', '=', c_pago.id)])
			comments1 = comments1+ con_pago.details+'\n'

		for c_enrega in  self.invoice_id_entrega:
			con_entrega = self.env['trxmexico.condiciones.entrega'].search([('id', '=', c_enrega.id)])
			comments12 = comments12+ con_entrega.details+'\n'
		
		for c_gen in  self.invoice_id_general:
			con_gen = self.env['trxmexico.condiciones.generales'].search([('id', '=', c_gen.id)])
			comments13 = comments13+ con_gen.details+'\n'

		comments = "CONDICIONES DE PAGO:"+'\n'+comments1+'\n'+"CONDICIONES DE ENTREGA:"+'\n'+comments12+'\n'+"CONDICIONES GENERALES:"+'\n'+comments13+'\n'
		self.comment = comments

	@api.multi
	def button_reset_taxes_trx_save(self):
		self.button_reset_taxes_trx()
		self.delete_workflow()
		self.create_workflow()

		return True
		# return {
		# 	'type': 'ir.actions.client',
  #           'tag':'reload',
  #           }

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
			if invoice.descuento_habilitar =='0':
				# Se crea una busqueda para cada concepto realcionado al Invoice
				for taxed in self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)]):
					if taxed.descuento:
						raise osv.except_osv('Descuento no permitido en Concepto', 'Se ha seleccionado un descuento para el producto %s, modifique el concepto e intente de nuevo.'%taxed.product_id.name)
					
					# Se obtiene el valor correspondiente si es en Dolares o en MXN
					if 'in_context' in self._context:
						unit_price = float(taxed.product_id.price_sell_mxn)
						taxed.sudo().write({'price_unit':unit_price})

					else:
						unit_price = float(taxed.product_id.list_price)
						taxed.sudo().write({'price_unit':unit_price})

					# Se obtiene el precio original de cada producto y se asigna a cada concepto
					price_subtotal = float(taxed.product_id.lst_price)
					# taxed.write({'price_unit': price_subtotal})

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
					invoice.write({'des_subtotal': 0.0})
			
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
						raise osv.except_osv(('Descuento en Concepto'),'La opción seleccinada no permite realizar el descuento de %s para el producto %s'%(taxed.descuento+'%',taxed.product_id.name))
					
					# Se obtiene el valor correspondiente si es en Dolares o en MXN
					if 'in_context' in self._context:
						# Si hay conceptos con descuento se realiza la operación para obtner el precio con el descuento de lo contrario se asigna el valor original de cada producto
						if taxed.descuento != 0:
							price_subtotal_s = float(taxed.product_id.price_sell_mxn) * float(float(taxed.descuento)/100)
							price_subtotal = float(taxed.product_id.price_sell_mxn) - float(price_subtotal_s)
							descuento = float(descuento) + float(price_subtotal_s)
						else:
							price_subtotal = float(taxed.product_id.price_sell_mxn)

					else:
						if taxed.descuento != 0:
							price_subtotal_s = float(taxed.product_id.lst_price) * float(float(taxed.descuento)/100)
							price_subtotal = float(taxed.product_id.lst_price) - float(price_subtotal_s)
							descuento = float(descuento) + float(price_subtotal_s)
						else:
							price_subtotal = float(taxed.product_id.lst_price)
					
					taxed.write({'price_unit': price_subtotal})

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
						raise osv.except_osv(('Multiple Impuesto por Producto'), 'Se ha seleccionado más de un impuesto para el producto %s, modifique el concepto e intente de nuevo, Por Favor.'%taxed.product_id.name)
				desc_total = float(subtotal) * float(float(invoice.descuento)/100)
				subtotal = float(subtotal) - float(desc_total)
				total_des = float(subtotal) + float(taxe_total)
				# Asignamos el valor que se descuenta a la variable des_subtotal
				invoice.write({'des_subtotal': desc_total,'subtotal_con_desc' : subtotal,'total_con_desc':total_des})

			# Creamos funcion para opción con descuento por concepto
			if invoice.descuento_habilitar =='2':
				descuento=0
				# Se crea una busqueda para cada concepto realcionado al Invoice
				for taxed in self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)]):
					# Si se coloca un descuento fuera de rango (0-100) se dispara Warning
					if int(taxed.descuento) > 100 or int(taxed.descuento) < 0:
						raise Warning("No se pueden hacer descuentos mayores a 100% ni menores del %0")

					if 'in_context' in self._context:
						# Si hay conceptos con descuento se realiza la operación para obtner el precio con el descuento de lo contrario se asigna el valor original de cada producto
						if taxed.descuento != 0:
							price_subtotal_s = float(taxed.product_id.price_sell_mxn) * float(float(taxed.descuento)/100)
							price_subtotal = float(taxed.product_id.price_sell_mxn) - float(price_subtotal_s)
							descuento = float(descuento) + float(price_subtotal_s)
						else:
							price_subtotal = float(taxed.product_id.price_sell_mxn)
					else:
						# Si hay conceptos con descuento se realiza la operación para obtner el precio con el descuento de lo contrario se asigna el valor original de cada producto
						if taxed.descuento != 0:
							price_subtotal_s = float(taxed.product_id.lst_price) * float(float(taxed.descuento)/100)
							price_subtotal = float(taxed.product_id.lst_price) - float(price_subtotal_s)
							descuento = float(descuento) + float(price_subtotal_s)
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
				invoice.write({'des_subtotal': descuento})


		# Se re-escribe sobre el Invoice que se esta trabajando
		return self.with_context(ctx).write({'invoice_line': []})

	# Boton que nos sirve para enviar la cotizacioón den PDF por mail
	def enviar_cotizacion_partner(self, cr, uid,ids, context=None):
		# servidor_ids = self.pool.get('res.users').search(cr, uid, [('id', '=', uid)])[0]
		servidor_ids = self.pool.get('res.users').browse(cr, uid, uid)
		print servidor_ids.login
		# Obtenemos los valores de la cotización
		cotizacion_id = self.pool.get('account.invoice').browse(cr, uid, ids[0])
		# Se obtiene el servidor por cada usuario 
		servidor_id = self.pool.get('ir.mail_server').search(cr, uid, [('smtp_user', '=', servidor_ids.login)])
		# Se obtiene si el usuario tiene un servidor para mandar mails
		if len(servidor_id):
			servidor = servidor_id[0]
		else:
			raise osv.except_osv(("¡Error!"), ('Este usuario no tiene servidor de correo saliente configurado'))

		servidor = self.pool.get('ir.mail_server').browse(cr, uid, servidor)
		# Obtnemos los template para crear el PDF
		model_data_template_id = self.pool.get('ir.model.data').search(cr, uid, [('module', '=', 'trxmexico'), ('name', '=', 'template_cotizacion_trx')])[0]
		model_data_template = self.pool.get('ir.model.data').browse(cr, uid, model_data_template_id)
		template_id = model_data_template.res_id
		# Se obtiene el template PDF
		report_id = self.pool.get('ir.actions.report.xml').search(cr, uid, [('name','=','COTIZACION'), ('report_name', '=', 'COTIZACION')])[0]
		self.pool.get('email.template').write(cr, SUPERUSER_ID, template_id, {'mail_server_id': servidor.id, 'report_template': report_id}, context=context )
		# Obtenemos los receptores para enviar el mail  y la fecha de creación
		context["receptor_email"] = cotizacion_id.partner_id.email
		context['correo_from']=servidor_ids.login
		context['nombre_form']=servidor_ids.login	
		src_tstamp_str = tools.datetime.now().strftime(tools.misc.DEFAULT_SERVER_DATETIME_FORMAT)
		src_format = tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
		dst_format = DEFAULT_SERVER_DATETIME_FORMAT #format you want to get time in. 
		dst_tz_name = self.pool.get('res.users').browse(cr, uid, uid, context=context).tz or 'Mexico/General'
		_now = tools.misc.server_to_local_timestamp(src_tstamp_str, src_format, dst_format, dst_tz_name)
		context['fecha_cotizacion']=_now
		# Se hace el envio del mail
		self.pool['email.template'].send_mail(cr, uid, template_id, ids[0], force_send=True, context=context)

	# Función para la creación de un repositorio por cliente
	def attachment_docs_account(self, cr, uid, ids, context):
		# Obtenemos a que modelo pertnece
		project_id = self.pool.get('account.invoice').browse(cr, uid, ids, context)
		# Creamos un domain unico por registro
		domain = [('res_model', '=', "account.invoice"),('res_id','=',project_id.id)]
		res_id = ids and ids[0] or False
		# retornamos los valores para la creación del repositorio
		return {
			'name': _('Cotizaciones'),
			'domain': domain,
			'res_model': 'ir.attachment',
			'type': 'ir.actions.act_window',
			'view_id': False,
			'view_mode': 'kanban,tree,form',
			'view_type': 'form',
			'limit': 80,
			'context': "{'default_res_model': '%s','default_res_id': %d, 'default_id_account': '%s'}" % (self._name, res_id, ids[0]),
			'help': '<p class="oe_view_nocontent_create">Agregar nueva versión de Cotización</p>'
			}



account_invoice()

class account_invoice_line(models.Model):
	_name="account.invoice.line"
	_inherit="account.invoice.line"

	# Funcion compute para llenado del monto y el costo en MXN
	@api.one
	@api.depends('price_unit')
	def _compute_amount_mxn(self):
		# Obtnemos el id de la cotización a usar
		if self.invoice_id.id :
			invoice_id = self.env['account.invoice'].search([('id', '=', self.invoice_id.id)])
			if invoice_id.type_cotizacion == False:
				dolar_id = self.env['trxmexico.change.monetary'].search([('id', '=', 1)])
				mxn = float(self.price_unit) * float(dolar_id.price_dolar)
			else:
				mxn = float(self.product_id.price_sell_mxn)

			# Asignamos los valores correspondientes si es DLL o MXN
			self.price_sell_mxn =  mxn
			self.amount_mxn =  float(mxn) * float(self.quantity)


	#Campos TRXMexico account_invoice_line
	price_sell_mxn = fields.Float(string='Precio MXN', index=True, compute='_compute_amount_mxn')
	amount_mxn = fields.Float(string='Monto MXN', index=True, compute='_compute_amount_mxn')
	descuento = fields.Char(string='Descuento %', size=4)
	modificar_precio = fields.Boolean(string='Modificar Precio')

	# FUNCIONES PARA ACCOUNT_INVOICE_LINE
	def onchange_get_price_unit(self, cr, uid, ids, producto, quantity, price_unit,modificar_precio, context):
		res={}
		if modificar_precio == False:
			product_id = self.pool.get('product.product').browse(cr, uid, producto, context=context)
			if 'in_dolars' in context:
				res['price_unit'] =float(product_id.list_price)/1.16
			else:
				res['price_unit'] =float(product_id.price_sell_mxn)/1.16
		else:
			res['price_unit'] = price_unit
		
		return{'value':res}


account_invoice_line()

class trxmexico_condiciones_pago(models.Model):
	_name="trxmexico.condiciones.pago"
	_rec_name = 'details'

	#Campos TRXMexico trxmexico_condiciones_pago
	name = fields.Char(string='Condiciones de Pago')
	details = fields.Text(string='Descripción')
	account_id = fields.Many2many('account.invoice', 'account_invoice_rel', 'invoice_id','account_id', 'Condiciones de Pago', copy=False)


trxmexico_condiciones_pago()

class trxmexico_condiciones_entrega(models.Model):
	_name="trxmexico.condiciones.entrega"
	_rec_name = 'details'

	#Campos TRXMexico trxmexico_condiciones_entrega
	name = fields.Char(string='Condiciones de Pago')
	details = fields.Text(string='Descripción')
	account_id = fields.Many2many('account.invoice', 'account_invoice_rel', 'invoice_id_entrega','account_id', 'Condiciones de Entrega', copy=False)


trxmexico_condiciones_entrega()

class trxmexico_condiciones_generales(models.Model):
	_name="trxmexico.condiciones.generales"
	_rec_name = 'details'

	#Campos TRXMexico trxmexico_condiciones_generales
	name = fields.Char(string='Condiciones de Pago')
	details = fields.Text(string='Descripción')
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

	# Compute para sacar el costo la fecha anteriror
	@api.model
	def _default_date_before(self):
		prices_id = self.env['trxmexico.change.monetary'].search([('id', '=', 1)])
		if prices_id:
			fecha = prices_id.fecha_cambio

		return fecha
	#Campos TRXMexico trxmexico_change_monetary
	price_dolar = fields.Float(string='Pesos')
	price_before = fields.Float(string='Costo anterior', default=_default_price_before)
	currency_id = fields.Many2one('res.currency',string='Tip de moneda', default=_default_curreny)
	fecha_cambio = fields.Datetime(string='Fecha y Hora del último cambio', default=_default_date_before)

	# Funcion que permite sobreescribir el mismo regitro y elimina los registros basura
	@api.multi
	def button_change_money(self):
		# Se busca el primer registro y se asigna el valor del dolar
		prices_id = self.env['trxmexico.change.monetary'].search([('id', '=', 1)])
		fecha = fields.datetime.now()
		prices_id.write({'price_dolar':self.price_dolar,'fecha_cambio':fecha})
		self.fecha_cambio = fields.datetime.now()
		# Los registros sobrantes existentes son eliminados
		for price_delete in self.env['trxmexico.change.monetary'].search([('id', '>', 1)]):
			self.env['trxmexico.change.monetary'].search([('id','=', price_delete.id)]).unlink()



trxmexico_change_monetary()

class ir_attachment(models.Model):
    _name = 'ir.attachment'
    _inherit = 'ir.attachment'

    # Boton para agregado masivo de clientes
    def asignar_partner(self, cr, uid, ids, context=None): 
        # Declaramos el diccionario para la creación de un partner y obtenemos el archivo que se subio
        vals={}
        attachment_dic = self.pool.get('ir.attachment').read(cr, uid, ids, ['name', 'store_fname', 'datas_fname'], context=context)
        filename = attachment_dic[0]['store_fname']
        datas_fname = attachment_dic[0]['datas_fname']

        file_name, file_extension = os.path.splitext(datas_fname)

        archivo_cargado = ODOO_HOME + '.local/share/Odoo/filestore/' + cr.dbname + '/' + filename
        # Consusmimos el script para el parseo del excel, obteniendo los valores
        datos_partner = cargar_MA(archivo_cargado)
        # Por cada fila del xls creamos un registro con los valores que corresponden a la vista
        for dato in datos_partner:
        	if dato['Estatus'] == 'Activo':
        		status = 'ACTIVO'
        	else:
        		status = 'NO_ACTIVO'
        	vals['clave_partner'] = int(dato['Clave'])
        	vals['status_partner'] = status
        	vals['name'] = dato['Nombre']
        	vals['rfc_partner'] = dato['RFC']
        	vals['domicilio_partner'] = dato['Calle']
        	vals['phone'] = dato['Telefono']
        	vals['email'] = dato['email']

        	# Creamos un nuevo registro en res.partner con los valores del diccionario
        	new_id = self.pool.get('res.partner').create(cr,uid, vals, context=context)
        return new_id

    def asignar_products(self, cr, uid, ids, context=None): 
        # Declaramos el diccionario para la creación de un partner y obtenemos el archivo que se subio
        vals={}
        attachment_dic = self.pool.get('ir.attachment').read(cr, uid, ids, ['name', 'store_fname', 'datas_fname'], context=context)
        filename = attachment_dic[0]['store_fname']
        datas_fname = attachment_dic[0]['datas_fname']

        file_name, file_extension = os.path.splitext(datas_fname)

        archivo_cargado = ODOO_HOME + '.local/share/Odoo/filestore/' + cr.dbname + '/' + filename
        # Consusmimos el script para el parseo del excel, obteniendo los valores
        datos_partner = cargar_Productos(archivo_cargado)
        # Por cada fila del xls creamos un registro con los valores que corresponden a la vista
        for dato in datos_partner:
        	vals['name'] = dato['clave']
        	vals['description'] = dato['description']
        	vals['list_price'] = dato['dolares']
        	vals['price_sell_mxn'] = dato['pesos']

        	# Creamos un nuevo registro en product.product con los valores del diccionario
        	new_id = self.pool.get('product.product').create(cr,uid, vals, context=context)
        return new_id

ir_attachment()









