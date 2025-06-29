from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_abc_analysis_reports.library import xlsxwriter

from . import setu_excel_formatter
import base64
from io import BytesIO

class SetuABCSalesFrequencyAnalysisReport(models.TransientModel):
    _name = 'setu.abc.sales.frequency.analysis.report'
    _description = """
        ABC Sales Frequency Analysis Report / ABC Analysis for Order Frequency
        Based ABC-analysis – is the famous Pareto principle, which states that 20% of efforts give 80% of the result.    
    """

    stock_file_data = fields.Binary('Stock Movement File')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")
    # warehouses_ids = fields.Many2many("stock.warehouse", 'abc_sale_freq_analysis_report_warehouse_rel',
    #                                   'abc_sale_freq_analysis_report_id',
    #                                   'warehouses_id',
    #                                   string="Warehouses",
    #                                   compute="_compute_warehouses_ids")
    abc_analysis_type = fields.Selection([('all', 'All'),
                                          ('highest_order', 'Highest Order Frequency (A)'),
                                          ('medium_order', 'Average Order Frequency (B)'),
                                          ('lowest_order', 'Lowest Order Frequency (C)')], "ABC Classification",
                                         default="all")
    
    @api.constrains('start_date', 'end_date')
    def _check_date_validation(self):
        """
            Added By: Shivam Pandya | Date: 24 Oct,2024 | Task: 898
            Use: checks Start date must be earlier than the End date
        """
        if self.start_date > self.end_date:
            raise ValidationError(_("The Start Date must be earlier than the End Date."))


    # @api.depends('company_ids')
    # def _compute_warehouses_ids(self):
    #     """
    #         Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
    #         Purpose: If user select companies from wizard then return warehouses based on companies
    #         otherwise return all warehouses
    #     :return:
    #     """
    #     for record in self:
    #         if record.company_ids:
    #             warehouses = self.env['stock.warehouse'].search(
    #                 [('company_id', 'child_of', record.company_ids.ids)])
    #             record.warehouses_ids = warehouses if warehouses else False
    #         else:
    #             warehouses = self.env['stock.warehouse'].search([])
    #             record.warehouses_ids = warehouses if warehouses else False

    @staticmethod
    def get_file_name():
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare name for xls report
        :return:
        """
        filename = "abc_sales_frequency_analysis_report.xlsx"
        return filename

    @staticmethod
    def create_excel_workbook(file_pointer):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose:This method will use for prepare workbook and return excel workbook
        :param file_pointer:
        :return:
        """
        workbook = xlsxwriter.Workbook(file_pointer)
        return workbook

    @staticmethod
    def create_excel_worksheet(workbook, sheet_name):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare worksheet with specific rows
        :param workbook:
        :param sheet_name:
        :return:
        """
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.set_default_row(22)
        # worksheet.set_border()
        return worksheet

    @staticmethod
    def set_column_width(worksheet):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for set column width in xls worksheet
        :param workbook:
        :param worksheet:
        :return:
        """
        worksheet.set_column(0, 1, 25)
        worksheet.set_column(2, 7, 16)

    @staticmethod
    def set_format(workbook, wb_format):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use prepare format for title in xls worksheet
        :param workbook:
        :param wb_format:
        :return:
        """
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        """
            Author: Kinnari Tank | Date: 11th Oct,2024 | Task: 1000
            Purpose: THis method will use for prepare title in xls worksheet and add start date and end date in xls report
        :param workbook:
        :param worksheet:
        :return:
        """
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 7, "ABC Sales Frequency Analysis Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        worksheet.write(2, 0, "Start Date", wb_format_left)
        worksheet.write(3, 0, "End Date", wb_format_left)
        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align': 'center', 'bold': True,
                                                      'font_color': 'red'})
        worksheet.write(2, 1, self.start_date, wb_format_center)
        worksheet.write(3, 1, self.end_date, wb_format_center)

    def get_abc_sales_frequency_analysis_report_data(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for fetch data from query based on user inputs.
        :return:
        """
        start_date = self.start_date
        end_date = self.end_date
        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search([('id', 'child_of', self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get('allowed_company_ids', False) or self.env.user.company_ids.ids) or {}

        warehouses = self.warehouse_ids and set(self.warehouse_ids.ids) or {}
        query = """
                Select * from get_abc_sales_frequency_analysis_data('%s','%s','%s','%s','%s','%s', '%s')
            """ % (company_ids, products, category_ids, warehouses, start_date, end_date, self.abc_analysis_type)
        # print(query)
        self._cr.execute(query)
        sales_data = self._cr.dictfetchall()
        return sales_data

    def prepare_data_to_write(self, stock_data={}):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare warehouse wise data to download warehouse wise separate sheet
        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key, False):
                warehouse_wise_data[key] = {data.get('product_id'): data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id'): data})
        return warehouse_wise_data

    def download_report(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method return xls worksheet when user click on excel report button from wizard.
        :return:
        """
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_abc_sales_frequency_analysis_report_data()
        warehouse_wise_analysis_data = self.prepare_data_to_write(stock_data=stock_data)
        if not warehouse_wise_analysis_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in warehouse_wise_analysis_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 5
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for abc_data_key, abc_data_value in stock_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, abc_data_value, row=row_no)
        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'stock_file_data': file_data})
        file_pointer.close()
        return {
            'name': 'ABC Sales Frequency Analysis Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/setu_abc_download_document?model=setu.abc.sales.frequency.analysis.report&field=stock_file_data&id=%s&filename=%s' % (
            self.id, file_name),
            'target': 'self',
        }

    def download_report_in_listview(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for return list view when user click on view data button from wizard
            and return graph view of reports when user click on view graph button from wizard.
        :return:
        """
        stock_data = self.get_abc_sales_frequency_analysis_report_data()
        #print(stock_data)
        for abc_data_value in stock_data:
            abc_data_value['wizard_id'] = self.id
            self.create_data(abc_data_value)
        graph_view_id = self.env.ref('setu_abc_analysis_reports.setu_abc_sales_frequency_analysis_bi_report_graph').id
        list_view_id = self.env.ref('setu_abc_analysis_reports.setu_abc_sales_frequency_analysis_bi_report_list').id
        is_graph_first = self.env.context.get('graph_report', False)
        report_display_views = []
        viewmode = ''
        if is_graph_first:
            report_display_views.append((graph_view_id, 'graph'))
            report_display_views.append((list_view_id, 'list'))
            viewmode = "graph,list"
        else:
            report_display_views.append((list_view_id, 'list'))
            report_display_views.append((graph_view_id, 'graph'))
            viewmode = "list,graph"
        report_date = self.env['setu.abc.configuration'].generate_report_date(self.start_date, self.end_date)

        return {
            'name': _('ABC Sales Frequency Analysis ({})'.format(report_date)),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.abc.sales.frequency.analysis.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def create_data(self, data):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for remove specific records from data
            and create record in bi report module
        :param data:
        :return:
        """
        del data['company_name']
        del data['product_name']
        del data['warehouse_name']
        del data['category_name']
        del data['cum_total_orders_per']
        return self.env['setu.abc.sales.frequency.analysis.bi.report'].create(data)

    def write_report_data_header(self, workbook, worksheet, row):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for add header in xls worksheet with highlighting color and background
        :param workbook:
        :param worksheet:
        :param row:
        :return:
        """
        self.set_report_title(workbook, worksheet)
        self.set_column_width(worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        worksheet.set_row(row, 30)
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        odd_normal_right_format.set_text_wrap()
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format.set_text_wrap()
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        normal_left_format.set_text_wrap()
        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Category', normal_left_format)
        worksheet.write(row, 2, 'Company', normal_left_format)
        worksheet.write(row, 3, 'Warehouse', normal_left_format)
        worksheet.write(row, 4, 'Total Sales', even_normal_right_format)
        worksheet.write(row, 5, 'Total Orders', odd_normal_right_format)
        worksheet.write(row, 6, 'Total Orders(%)', even_normal_right_format)
        # worksheet.write(row, 5, 'Cum. Sales Amount (%)', even_normal_right_format)
        worksheet.write(row, 7, 'ABC Classification', odd_normal_right_format)
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        """
           Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
           Purpose: This method will use for add records in worksheet with appropriate format
        """
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        odd_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)
        worksheet.write(row, 0, data.get('product_name', ''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name', ''), normal_left_format)
        worksheet.write(row, 2, data.get('company_name', ''), normal_left_format)
        worksheet.write(row, 3, data.get('warehouse_name', ''), normal_left_format)
        worksheet.write(row, 4, data.get('sales_qty', ''), even_normal_right_format)
        worksheet.write(row, 5, data.get('total_orders', ''), odd_normal_right_format)
        worksheet.write(row, 6, data.get('total_orders_per', ''), even_normal_right_format)
        # worksheet.write(row, 5, data.get('cum_sales_amount_per', ''), even_normal_right_format)
        worksheet.write(row, 7, data.get('analysis_category', ''), odd_normal_center_format)
        return worksheet
