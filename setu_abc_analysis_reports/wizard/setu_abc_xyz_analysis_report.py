from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_abc_analysis_reports.library import xlsxwriter
from . import setu_excel_formatter
import base64
from io import BytesIO


class SetuABCYZAnalysisReport(models.TransientModel):
    _name = 'setu.abc.xyz.analysis.report'
    _description = """
        Inventory ABC-XYZ Analysis Report
            Based ABC-analysis – is the famous Pareto principle, which states that 20% of efforts give 80% of the result.            
            
            XYZ Analysis is always done for the current Stock in Inventory and aims at classifying the items into three classes on the basis of their Inventory values. 
            The current value of the items/variants in the Inventory alone is taken into consideration for the Analysis and it is not possible to do this analysis for any other dates. 
    """

    stock_file_data = fields.Binary('Stock Movement File')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")
    abc_analysis_type = fields.Selection([('all', 'All'),
                                          ('high_sales', 'High Sales (A)'),
                                          ('medium_sales', 'Medium Sales (B)'),
                                          ('low_sales', 'Low Sales (C)')], "ABC Classification", default="all")

    inventory_analysis_type = fields.Selection([('all', 'All'),
                                                ('high_stock', 'X Class'),
                                                ('medium_stock', 'Y Class'),
                                                ('low_stock', 'Z Class')], "XYZ Classification", default="all")

    @api.constrains('start_date', 'end_date')
    def _check_date_validation(self):
        """
            Added By: Shivam Pandya | Date: 24 Oct,2024 | Task: 898
            Use: checks Start date must be earlier than the End date
        """
        if self.start_date > self.end_date:
            raise ValidationError(_("The Start Date must be earlier than the End Date."))


    @staticmethod
    def get_file_name():
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare name for xls report
        :return:
        """
        filename = "abc_xyz_analysis_report.xlsx"
        return filename

    @staticmethod
    def create_excel_workbook(file_pointer):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare workbook and return excel workbook
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
        worksheet.set_column(2, 11, 14)

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
        worksheet.merge_range(0, 0, 1, 11, "ABC-XYZ Combined Analysis Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        worksheet.write(2, 0, "Start Date", wb_format_left)
        worksheet.write(3, 0, "End Date", wb_format_left)
        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align': 'center', 'bold': True,
                                                      'font_color': 'red'})
        worksheet.write(2, 1, self.start_date, wb_format_center)
        worksheet.write(3, 1, self.end_date, wb_format_center)

    def get_abc_xyz_analysis_report_data(self):
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

        query = """
                Select * from get_abc_xyz_analysis_report('%s','%s','%s','%s','%s','%s', '%s')
            """ % (company_ids, products, category_ids, start_date, end_date, self.abc_analysis_type,
                   self.inventory_analysis_type)
        # print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return stock_data

    def prepare_data_to_write(self, stock_data={}):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for prepare company wise data to generate company wise result
        """
        company_wise_data = {}
        for data in stock_data:
            key = (data.get('company_id'), data.get('company_name'))
            if not company_wise_data.get(key, False):
                company_wise_data[key] = {data.get('product_id'): data}
            else:
                company_wise_data.get(key).update({data.get('product_id'): data})
        return company_wise_data

    def download_report(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method return xls worksheet when user click on excel report button from wizard.
        :return:
        """
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_abc_xyz_analysis_report_data()
        warehouse_wise_analysis_data = self.prepare_data_to_write(stock_data=stock_data)
        if not warehouse_wise_analysis_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in warehouse_wise_analysis_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 5
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for abc_xyz_data_key, abc_xyz_data_value in stock_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, abc_xyz_data_value, row=row_no)
        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'stock_file_data': file_data})
        file_pointer.close()
        return {
            'name': 'ABC-XYZ Analysis Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/setu_abc_download_document?model=setu.abc.xyz.analysis.report&field=stock_file_data&id=%s&filename=%s' % (
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
        stock_data = self.get_abc_xyz_analysis_report_data()
        #print(stock_data)
        for abc_data_value in stock_data:
            abc_data_value['wizard_id'] = self.id
            self.create_data(abc_data_value)
        graph_view_id = self.env.ref('setu_abc_analysis_reports.setu_abc_xyz_analysis_bi_report_graph').id
        list_view_id = self.env.ref('setu_abc_analysis_reports.setu_abc_xyz_analysis_bi_report_list').id
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
            'name': _('ABC-XYZ Combined Analysis ({})'.format(report_date)),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.abc.xyz.analysis.bi.report',
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
        del data['category_name']
        del data['cum_sales_amount_per']
        return self.env['setu.abc.xyz.analysis.bi.report'].create(data)

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
        worksheet.set_row(row, 28)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        worksheet.set_row(row, 30)
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        odd_normal_right_format.set_text_wrap()
        even_normal_right_format.set_text_wrap()
        normal_left_format.set_text_wrap()
        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Category', normal_left_format)
        worksheet.write(row, 2, 'Company', normal_left_format)
        worksheet.write(row, 3, 'Total Sales', odd_normal_right_format)
        worksheet.write(row, 4, 'Total Sales Amount', even_normal_right_format)
        worksheet.write(row, 5, 'Total Orders', odd_normal_right_format)
        worksheet.write(row, 6, 'Total Sales Amount (%)', even_normal_right_format)
        # worksheet.write(row, 5, 'Cum. Sales Amount (%)', even_normal_right_format)
        worksheet.write(row, 7, 'ABC Classification', odd_normal_right_format)
        worksheet.write(row, 8, 'Current Stock', even_normal_right_format)
        worksheet.write(row, 9, 'Stock Value', odd_normal_right_format)
        worksheet.write(row, 10, 'XYZ Classification', even_normal_right_format)
        worksheet.write(row, 11, 'ABC-XYZ Classification', odd_normal_right_format)
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: This method will use for add records in worksheet with appropriate format
        :param workbook:
        :param worksheet:
        :param data:
        :param row:
        :return:
        """
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)
        worksheet.write(row, 0, data.get('product_name', ''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name', ''), normal_left_format)
        worksheet.write(row, 2, data.get('company_name', ''), normal_left_format)
        worksheet.write(row, 3, data.get('sales_qty', ''), odd_normal_right_format)
        worksheet.write(row, 4, data.get('sales_amount', ''), even_normal_right_format)
        worksheet.write(row, 5, data.get('total_orders', ''), odd_normal_right_format)
        worksheet.write(row, 6, data.get('sales_amount_per', ''), even_normal_right_format)
        # worksheet.write(row, 5, data.get('cum_sales_amount_per', ''), even_normal_right_format)
        worksheet.write(row, 7, data.get('abc_classification', ''), odd_normal_center_format)
        worksheet.write(row, 8, data.get('current_stock', ''), even_normal_right_format)
        worksheet.write(row, 9, data.get('stock_value', ''), odd_normal_right_format)
        worksheet.write(row, 10, data.get('xyz_classification', ''), even_normal_center_format)
        worksheet.write(row, 11, data.get('combine_classification', ''), odd_normal_center_format)
        return worksheet
