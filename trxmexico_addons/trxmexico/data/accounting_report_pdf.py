from datetime import datetime, date, timedelta
from openerp.osv import osv, fields
from openerp.report import report sxw


class accounting_report_pdf(osv.AbstractModel):
	#nombre para  report.module.name.template.id
	_name = 'report.full_accounting_report.full_accounting_report_pdf'

	#Se taeran todos los periodos sin duplicar
	def _get_periods(self,docs):
		array_period = []
		for object in docs:
			array_period.append(object.period_id.name)
			# Para borrar duplicados
		periods = list(set(array_period))
		return periods

	# La función para pasar el xml en archivo
	def render_htm(self, cr, uid, ids, data=None, context=None):
		report_obj = self.pool['report']
		report = report_obj.get_report_from_name(cr, uid, 'full_accounting_report.full_accounting_report_pdf')

		docargs = {
			'doc_ids' : ids,
			'doc_model' : report.model,
			'docs' : self.pool[report.model].browse(cr, uid, ids, context=context),
		}
		return report_obj.render(cr, uid, ids, 'full_accounting_report.full_accounting_report_pdf', docargs, context=context)

accounting_report_pdf()
