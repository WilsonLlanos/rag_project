import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Erro ao conectar no SQL: {e}")
        return None

# --- FERRAMENTAS DO RAG HÍBRIDO (TOOL CALLING) ---

def consultar_saldo_contrato(numero_contrato: str = None, codigo_lote: str = None):
    """
    Busca os dados de um Lote a partir do Número do Contrato (Referência) OU do ID do Lote.
    """
    if not numero_contrato and not codigo_lote:
        return {"erro": "É necessário fornecer um número de contrato ou um ID de lote para a pesquisa."}

    conn = get_db_connection()
    if not conn:
        return {"erro": "Falha na conexão com o banco de dados."}
    
    try:
        cursor = conn.cursor()
        
        # Lógica condicional: Constrói a query dependendo do que o utilizador perguntou
        if numero_contrato:
            query_lote = """
                SELECT LoteId, CodigoLote, FornecedorId, QuantidadeSacas, QuantidadeOriginal, Qualidade, StatusLote
                FROM Lotes
                JOIN HistoricoLotes H ON L.Id = H.LoteId
                WHERE H.Referencia = ? AND H.TipoMovimento = 'E'
            """
            cursor.execute(query_lote, (numero_contrato,))
        else:
            query_lote = """
                SELECT LoteId, CodigoLote, FornecedorId, QuantidadeSacas, QuantidadeOriginal, Qualidade, StatusLote
                FROM Lotes
                WHERE CodigoLote = ?
            """
            cursor.execute(query_lote, (codigo_lote,))
            
        row = cursor.fetchone()
        
        if not row:
            termo = numero_contrato if numero_contrato else codigo_lote
            return {"mensagem": f"Aviso: Nenhum lote encontrado para a pesquisa: {termo}."}
            
        id_encontrado = row.LoteId
        
        # Agora busca o histórico usando o ID encontrado
        query_historico = "SELECT TipoMovimento, Quantidade, Referencia, DataMovimento FROM HistoricoLotes WHERE LoteId = ? ORDER BY DataMovimento ASC"
        cursor.execute(query_historico, (id_encontrado,))
        historico_rows = cursor.fetchall()
        
        historico_lista = []
        for h in historico_rows:
            historico_lista.append({
                "movimento": h.TipoMovimento,
                "quantidade": float(h.Quantidade),
                "documento": h.Referencia,
                "data": h.DataMovimento.strftime("%Y-%m-%d %H:%M")
            })

        return {
            "codigo_lote_interno": id_encontrado,
            "dados_do_lote": {
                # "tipo_cafe": row.TipoCafe,
                "codigo_lote": row.CodigoLote,
                "Qualidade": row.Qualidade,
                "quantidade_original_comprada": float(row.QuantidadeOriginal),
                "saldo_atual_disponivel": float(row.QuantidadeSacas), 
                "status": row.StatusLote
                # "classificacao": row.Classificacao
            },
            "historico_de_movimentacoes": historico_lista
        }
    
    except Exception as e:
        return {"erro": f"Erro na consulta SQL: {str(e)}"}
    finally:
        if conn:
            conn.close()


def ajustar_residuo_lote_por_codigo_lote(codigo_lote: str):
    """
    Corrige o resíduo decimal de um lote.
    A IA deve usar esta função informando o LoteId obtido através da função consultar_saldo_contrato.
    """
    conn = get_db_connection()
    if not conn:
        return {"erro": "Falha na conexão com o banco de dados."}
    
    try:
        cursor = conn.cursor()
        # Regra de negócio gravada em pedra no Backend
        query = """
            UPDATE Lotes 
            SET QuantidadeSacas = 0.0, Status = 'Encerrado'
            WHERE CodigoLote = ? AND QuantidadeSacas > 0 AND QuantidadeSacas <= 0.01
        """
        cursor.execute(query, (codigo_lote,))
        linhas_afetadas = cursor.rowcount
        conn.commit()
        
        if linhas_afetadas > 0:
            # Registra no histórico que o sistema IA encerrou o lote
            query_log = "INSERT INTO HistoricoLotes (CodigoLote, TipoMovimento, Quantidade, Referencia, DataMovimento) VALUES (?, 'A', 0.0, 'AJUSTE_IA_SISTEMA', GETDATE())"
            cursor.execute(query_log, (codigo_lote,))
            conn.commit()
            return {"mensagem": f"Sucesso: O resíduo decimal do Lote ID {codigo_lote} foi corrigido e o lote foi Encerrado. Histórico atualizado."}
        else:
            return {"mensagem": f"Operação negada: O lote {codigo_lote} não existe ou o saldo é maior que 0.01 sacas."}
            
    except Exception as e:
        return {"erro": f"Erro na atualização SQL: {str(e)}"}
    finally:
        if conn:
            conn.close()

def consultar_fornecedor_por_nome(nome_fornecedor: str):
    """
    USADA PELO RAG_SERVICE.PY (GPT-4o / Tool Calling)
    Traz todos os dados do fornecedor pelo nome para a IA fazer a auditoria, ignorando filtros da tela.
    """
    conn = get_db_connection()
    if not conn:
        return {"erro": "Falha na conexão com o banco de dados."}

    try:
        cursor = conn.cursor()
        query = """SELECT FornecedorId, NomeFornecedor, CPF_CNPJ, QualidadeCafe, Ativo, Estado 
        FROM Fornecedores WHERE NomeFornecedor LIKE ?"""
        cursor.execute(query, ('%' + nome_fornecedor + '%',))
        row = cursor.fetchone()

        if not row:
            return {"mensagem": f"Fornecedor não encontrado: {nome_fornecedor}"}

        return {
            "fornecedor_id": row.FornecedorId,
            "nome_oficial": row.NomeFornecedor,
            "cnpj": row.CPF_CNPJ,
            "qualidade_cafe_que_vende": row.QualidadeCafe,
            "estado_origem": row.Estado,
            "cadastro_ativo": bool(row.Ativo)
        }

    except Exception as e:
        return {"erro": f"Erro na consulta SQL: {str(e)}"}
    finally:
        if conn:
            conn.close()


def listar_fornecedores_filtrados(tipo_cafe: str, estado: str):
    """
    Retorna uma lista de strings contendo apenas os nomes dos fornecedores ativos,
    filtrados pelo tipo de café autorizado e pelo estado de origem.
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        query = """
            SELECT NomeFornecedor
            FROM Fornecedores
            WHERE QualidadeCafe = ? AND Estado = ? AND Ativo = 1
            ORDER BY NomeFornecedor ASC
        """
        cursor.execute(query, (tipo_cafe, estado))
        rows = cursor.fetchall()
        
        # Converte os resultados em uma lista simples de strings contendo os nomes
        return [row.NomeFornecedor for row in rows]
    except Exception as e:
        print(f"Erro ao listar fornecedores filtrados: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def listar_todos_os_lotes():
    """
    Retorna todos os lotes do banco de dados para popular a tabela inicial do Streamlit.
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        # Busca os principais dados para a visão geral
        query = """
            SELECT LoteId, CodigoLote, Qualidade, QuantidadeSacas, QuantidadeOriginal, StatusLote
            FROM Lotes
            ORDER BY LoteId DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        lista_lotes = []
        for row in rows:
            lista_lotes.append({
                "ID Interno": row.LoteId,
                "Código do Lote": row.CodigoLote,
                "Qualidade": row.Qualidade,
                "Saldo Atual": float(row.QuantidadeSacas),
                "Qtd Original": float(row.QuantidadeOriginal),
                "Status": row.StatusLote
            })
            
        return lista_lotes
    except Exception as e:
        print(f"Erro ao listar todos os lotes: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def ajustar_residuo_lote_por_codigo_lote(codigo_lote: str):
    """
    Corrige o resíduo decimal de um lote atualizando o registro da guia de saída existente.
    """
    conn = get_db_connection()
    if not conn:
        return {"erro": "Falha na conexão com o banco de dados."}
    
    try:
        cursor = conn.cursor()
        
        # 1. Busca o Lote e o seu saldo (resíduo)
        cursor.execute("SELECT LoteId, QuantidadeSacas FROM Lotes WHERE CodigoLote = ?", (codigo_lote,))
        row_lote = cursor.fetchone()
        
        if not row_lote:
            return {"mensagem": f"Operação negada: Lote {codigo_lote} não encontrado."}
            
        lote_id = row_lote.LoteId
        residuo_lote = float(row_lote.QuantidadeSacas)
        
        if residuo_lote <= 0 or residuo_lote > 0.01:
            return {"mensagem": f"Operação negada: Saldo de {residuo_lote} não se enquadra na regra de resíduo."}

        # 2. Confirma a integridade matemática
        # CORREÇÃO: Removido o AS SaldoCalculado e usando índice [0] para evitar bugs do pyodbc
        cursor.execute("SELECT SUM(Quantidade) FROM HistoricoLotes WHERE LoteId = ?", (lote_id,))
        row_soma = cursor.fetchone()
        
        # Garante que não é None antes de converter
        saldo_historico = float(row_soma[0]) if row_soma and row_soma[0] else 0.0
        
        if round(residuo_lote, 6) != round(saldo_historico, 6):
            return {"mensagem": f"Inconsistência matemática: Lote=({residuo_lote}) vs Histórico=({saldo_historico})."}

        # 3. Busca o registro de saída ('G') existente
        cursor.execute("""
            SELECT TOP 1 Id, Quantidade 
            FROM HistoricoLotes 
            WHERE LoteId = ? AND TipoMovimento = 'G' 
            ORDER BY Id DESC
        """, (lote_id,))
        row_saida = cursor.fetchone()
        
        if not row_saida:
            return {"mensagem": f"Falha: Nenhuma guia de saída ('G') encontrada no lote {codigo_lote}."}
            
        historico_id = row_saida.Id
        quantidade_saida_atual = float(row_saida.Quantidade) 
        
        # 4. Faz os UPDATES em Transação
        nova_quantidade_saida = quantidade_saida_atual - residuo_lote
        
        # CORREÇÃO: Transformando nova_quantidade_saida em string (str) para forçar o Azure SQL 
        # a aceitar os decimais exatos sem dar erro de precisão (Truncation Error)
        cursor.execute("UPDATE HistoricoLotes SET Quantidade = ? WHERE Id = ?", (str(nova_quantidade_saida), historico_id))
        
        cursor.execute("UPDATE Lotes SET QuantidadeSacas = 0.0, StatusLote = 'Encerrado' WHERE LoteId = ?", (lote_id,))
        
        conn.commit()
        return {"mensagem": f"Sucesso! O resíduo de {residuo_lote} foi incorporado à saída existente no histórico. Lote {codigo_lote} zerado e encerrado."}
        
    except Exception as e:
        conn.rollback()
        # PARA OBSERVABILIDADE: Imprime o erro técnico no terminal do FastAPI
        print(f"\n[DEBUG SQL ERROR] Falha ao ajustar resíduo: {str(e)}\n")
        return {"erro": f"Erro interno no SQL: {str(e)}"}
    finally:
        if conn:
            conn.close()