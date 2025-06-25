from odoo import fields, models, api, _


class SetuABCSalesFrequencyAnalysisBIReport(models.TransientModel):
    _name = 'setu.abc.sales.frequency.analysis.bi.report'
    _description = """It helps to organize ABC sales frequency analysis data in listview and graphview"""

    name = fields.Char()
    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    warehouse_id = fields.Many2one("stock.warehouse")
    company_id = fields.Many2one("res.company", "Company")
    sales_qty = fields.Float("Total Sales")
    total_orders = fields.Integer("Total Orders")
    total_orders_per = fields.Float("Total Orders (%)")
    # cum_total_orders_per = fields.Float("Cum. Total Orders (%)")
    analysis_category = fields.Char("ABC Classification")
    wizard_id = fields.Many2one("setu.abc.sales.frequency.analysis.report")


    def action_setu_abc_sales_frequency_analysis_bi_report(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: User can not able to open record form view from report list view
        """
        return {}

    @api.model_create_multi
    def create(self, vals):
        records = super(SetuABCSalesFrequencyAnalysisBIReport, self).create(vals)
        for rec in records:
            rec.name = rec.get_display_name()
        return records

    def get_display_name(self):
        report_date = self.env['setu.abc.configuration'].generate_report_date(self.wizard_id.start_date, self.wizard_id.end_date)
        return 'ABC Sales Frequency Analysis ({})'.format(report_date)

    @api.depends('name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.get_display_name()
