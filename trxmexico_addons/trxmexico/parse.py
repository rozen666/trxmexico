#! -*- coding: utf-8 -*-

import psycopg2
import xlrd


def cast_str_to_int( s ):
    mto = str(s).split('.')[0]
    l = len(mto) - 1
    suma = 0
    for letra in mto:
        n = (10**l)*(ord(letra) - 48)
        l -= 1
        suma += n
    return suma


def cargar_MA( nombre_archivo ):

    archivo_excel_nombre = str(nombre_archivo)
    archivo = xlrd.open_workbook( archivo_excel_nombre )
    hoja = archivo.sheet_by_index(0)

    numero_registros = hoja.nrows
    #print "Numero de registros en la hoja: %d" % numero_registros
    r = 1
    lista_registros = []

    lista_dicc = []

    while r < numero_registros:

        v0 = hoja.cell_value( rowx=r, colx=0 )
        v1 = hoja.cell_value( rowx=r, colx=1 )
        v2 = hoja.cell_value( rowx=r, colx=2 )
        v3 = hoja.cell_value( rowx=r, colx=3 )
        v4 = hoja.cell_value( rowx=r, colx=4 )
        v5 = hoja.cell_value( rowx=r, colx=5 )        
        v6 = hoja.cell_value( rowx=r, colx=6 )        
     

        d = {
            'Clave':v0,
            'Estatus': v1,
            'Nombre': v2,
            'RFC': v3,
            'Calle': v4,
            'Telefono': v5,
            'email': v6,

            }
        
        lista_dicc.append( d )

        r += 1
	# print lista_dicc
    	
    return lista_dicc

def cargar_Productos( nombre_archivo ):

    archivo_excel_nombre = str(nombre_archivo)
    archivo = xlrd.open_workbook( archivo_excel_nombre )
    hoja = archivo.sheet_by_index(0)

    numero_registros = hoja.nrows
    #print "Numero de registros en la hoja: %d" % numero_registros
    r = 1
    lista_registros = []

    lista_dicc = []

    while r < numero_registros:

        v0 = hoja.cell_value( rowx=r, colx=0 )
        v1 = hoja.cell_value( rowx=r, colx=1 )
        v2 = hoja.cell_value( rowx=r, colx=2 )
        v3 = hoja.cell_value( rowx=r, colx=3 )
        v4 = hoja.cell_value( rowx=r, colx=4 )
        v5 = hoja.cell_value( rowx=r, colx=5 )        
     

        d = {
            'id':v0,
            'clave': v2,
            'description': v3,
            'dolares': v4,
            'pesos': v5,

            }
        
        lista_dicc.append( d )

        r += 1
    # print lista_dicc
        
    return lista_dicc

# print cargar_Productos("productos.xls")

