import pyodbc
import os
import json
from dotenv import load_dotenv
import datetime

load_dotenv()

# Fallback: pyodbc não está entre as bibliotecas com auto-instrumentação do
# azure-monitor-opentelemetry (cobre psycopg2/pymysql/sqlite3, não ODBC).
# Só habilitar se a verificação em Application Insights (tasks.md 3.2) confirmar
# que chamadas SQL via pyodbc não aparecem como dependências. Requer adicionar
# opentelemetry-instrumentation-dbapi ao requirements.txt (atualmente só em beta).
#
# if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
#     from opentelemetry.instrumentation.dbapi import trace_integration
#     trace_integration(pyodbc, "connect", "odbc")

def get_db_connection():
    conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Erro ao conectar no SQL: {e}")
        return None

# --- OBSERVABILIDADE (AUDITORIA DE EVENTOS PARA O PROJETO MULTIAGENTES) ---

def criar_tabela_auditoria_se_nao_existir():
    """
    Garante a existência da tabela EventosAuditoria, usada para registrar
    cada chamada de ferramenta feita pela IA. É a fonte de dados que o
    projeto de multiagentes de incidentes vai consultar.
    """
    conn = get_db_connection()
    if not conn:
        print("Aviso: não foi possível verificar/criar a tabela EventosAuditoria (sem conexão).")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='EventosAuditoria' AND xtype='U')
            CREATE TABLE EventosAuditoria (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                DataHora DATETIME2 DEFAULT SYSDATETIME(),
                NomeFerramenta NVARCHAR(100) NOT NULL,
                ArgumentosSeguro NVARCHAR(MAX) NULL,
                Status NVARCHAR(20) NOT NULL,
                DuracaoMs INT NULL,
                MensagemErro NVARCHAR(MAX) NULL
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabela EventosAuditoria: {str(e)}")
    finally:
        if conn:
            conn.close()


def registrar_evento_auditoria(
    nome_ferramenta: str,
    argumentos_seguro: dict,
    status: str,
    duracao_ms: int,
    mensagem_erro: str = None
):
    """
    Grava um evento de auditoria de chamada de ferramenta pela IA.
    IMPORTANTE: 'argumentos_seguro' deve conter apenas os argumentos ainda
    tokenizados (antes da reidratação de PII) — nunca dados reais.
    """
    conn = get_db_connection()
    if not conn:
        print("Aviso: falha ao registrar evento de auditoria (sem conexão).")
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO EventosAuditoria (NomeFerramenta, ArgumentosSeguro, Status, DuracaoMs, MensagemErro)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                nome_ferramenta,
                json.dumps(argumentos_seguro, ensure_ascii=False),
                status,
                duracao_ms,
                mensagem_erro
            )
        )
        conn.commit()
    except Exception as e:
        print(f"Erro ao registrar evento de auditoria: {str(e)}")
    finally:
        if conn:
            conn.close()


# --- FINOPS (CONSUMO DE TOKENS/CUSTO DO AZURE OPENAI, PARA O CAP. 5 DO TCC) ---

def criar_tabela_consumo_llm_se_nao_existir():
    """
    Garante a existência da tabela EventosConsumoLLM, usada para registrar o
    consumo de tokens e o custo estimado de cada chamada ao Azure OpenAI
    (chat e embeddings). Não reaproveita EventosAuditoria: aquela tabela é
    para tool calls e já tem um consumidor externo definido (o projeto de
    multiagentes de incidentes).
    """
    conn = get_db_connection()
    if not conn:
        print("Aviso: não foi possível verificar/criar a tabela EventosConsumoLLM (sem conexão).")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='EventosConsumoLLM' AND xtype='U')
            CREATE TABLE EventosConsumoLLM (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                DataHora DATETIME2 DEFAULT SYSDATETIME(),
                IdAtendimento NVARCHAR(36) NOT NULL,
                TipoChamada NVARCHAR(20) NOT NULL,
                NomeDeployment NVARCHAR(100) NOT NULL,
                NumeroIteracaoReact INT NULL,
                PromptTokens INT NOT NULL,
                CompletionTokens INT NULL,
                TotalTokens INT NOT NULL,
                CustoEstimadoUsd DECIMAL(10,6) NOT NULL
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabela EventosConsumoLLM: {str(e)}")
    finally:
        if conn:
            conn.close()


def registrar_evento_consumo_llm(
    id_atendimento: str,
    tipo_chamada: str,
    nome_deployment: str,
    numero_iteracao_react: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    custo_estimado_usd: float
):
    """
    Grava um evento de consumo de tokens de uma chamada ao Azure OpenAI
    (tipo_chamada: 'Chat' ou 'Embedding'). Nunca deve derrubar a resposta ao
    usuário — qualquer falha aqui só é logada, igual ao padrão já usado em
    registrar_evento_auditoria.
    """
    conn = get_db_connection()
    if not conn:
        print("Aviso: falha ao registrar evento de consumo de LLM (sem conexão).")
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO EventosConsumoLLM (
                IdAtendimento, TipoChamada, NomeDeployment, NumeroIteracaoReact,
                PromptTokens, CompletionTokens, TotalTokens, CustoEstimadoUsd
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_atendimento,
                tipo_chamada,
                nome_deployment,
                numero_iteracao_react,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                custo_estimado_usd
            )
        )
        conn.commit()
    except Exception as e:
        print(f"Erro ao registrar evento de consumo de LLM: {str(e)}")
    finally:
        if conn:
            conn.close()


# --- FERRAMENTAS DO RAG HÍBRIDO (TOOL CALLING) ---

# def consultar_saldo_contrato(numero_contrato: str = None, codigo_lote: str = None):
#     """
#     Busca os dados de um Lote a partir do Número do Contrato (Referência) OU do ID do Lote.
#     """
#     if not numero_contrato and not codigo_lote:
#         return {"erro": "É necessário fornecer um número de contrato ou um ID de lote para a pesquisa."}

#     conn = get_db_connection()
#     if not conn:
#         return {"erro": "Falha na conexão com o banco de dados."}
    
#     try:
#         cursor = conn.cursor()
        
#         # Lógica condicional: Constrói a query dependendo do que o utilizador perguntou
#         if numero_contrato:
#             query_lote = """
#                 SELECT LoteId, CodigoLote, FornecedorId, QuantidadeSacas, QuantidadeOriginal, Qualidade, StatusLote
#                 FROM Lotes
#                 JOIN HistoricoLotes H ON L.Id = H.LoteId
#                 WHERE H.Referencia = ? AND H.TipoMovimento = 'E'
#             """
#             cursor.execute(query_lote, (numero_contrato,))
#         else:
#             query_lote = """
#                 SELECT LoteId, CodigoLote, FornecedorId, QuantidadeSacas, QuantidadeOriginal, Qualidade, StatusLote
#                 FROM Lotes
#                 WHERE CodigoLote = ?
#             """
#             cursor.execute(query_lote, (codigo_lote,))
            
#         row = cursor.fetchone()
        
#         if not row:
#             termo = numero_contrato if numero_contrato else codigo_lote
#             return {"mensagem": f"Aviso: Nenhum lote encontrado para a pesquisa: {termo}."}
            
#         id_encontrado = row.LoteId
        
#         # Agora busca o histórico usando o ID encontrado
#         query_historico = "SELECT TipoMovimento, Quantidade, Referencia, DataMovimento FROM HistoricoLotes WHERE LoteId = ? ORDER BY DataMovimento ASC"
#         cursor.execute(query_historico, (id_encontrado,))
#         historico_rows = cursor.fetchall()
        
#         historico_lista = []
#         for h in historico_rows:
#             historico_lista.append({
#                 "movimento": h.TipoMovimento,
#                 "quantidade": float(h.Quantidade),
#                 "documento": h.Referencia,
#                 "data": h.DataMovimento.strftime("%Y-%m-%d %H:%M")
#             })

#         return {
#             "codigo_lote_interno": id_encontrado,
#             "dados_do_lote": {
#                 # "tipo_cafe": row.TipoCafe,
#                 "codigo_lote": row.CodigoLote,
#                 "Qualidade": row.Qualidade,
#                 "quantidade_original_comprada": float(row.QuantidadeOriginal),
#                 "saldo_atual_disponivel": float(row.QuantidadeSacas), 
#                 "status": row.StatusLote
#                 # "classificacao": row.Classificacao
#             },
#             "historico_de_movimentacoes": historico_lista
#         }
    
#     except Exception as e:
#         return {"erro": f"Erro na consulta SQL: {str(e)}"}
#     finally:
#         if conn:
#             conn.close()

def filtrar_lotes(
    codigo_lote: str = None,
    fornecedor_nome: str = None,
    qualidade: str = None,
    status: str = None,
    apenas_com_residuos: bool = False
):
    """
    Busca Lotes e respectivos Históricos de Movimentação de forma dinâmica.
    Agrupa os dados em estrutura Master-Detail para economizar tokens do LLM.
    """
    # IMPORTANTE: Garanta o import do datetime no topo do seu database.py (import datetime)
    conn = get_db_connection()
    if not conn:
        return {"erro": "Falha na conexão com o banco de dados."}
    
    try:
        cursor = conn.cursor()
        
        # A query dinâmica com LEFT JOIN para garantir que lotes sem histórico também apareçam
        query = """
            SELECT L.CodigoLote, F.NomeFornecedor AS Fornecedor, L.QuantidadeSacas AS SaldoAtual, 
                   L.Qualidade, L.StatusLote, L.QuantidadeOriginal,
                   HL.TipoMovimento, HL.DataMovimento, HL.Quantidade AS QuantidadeMovimento
            FROM Lotes L
            LEFT JOIN HistoricoLotes HL ON HL.LoteId = L.LoteId
            JOIN Fornecedores F ON F.FornecedorId = L.FornecedorId
            WHERE 1=1
        """
        parametros = []
        
        # --- Lógica de Filtros Dinâmicos ---
        if codigo_lote:
            query += " AND L.CodigoLote = ?"
            parametros.append(codigo_lote)
        if fornecedor_nome:
            query += " AND F.Nome LIKE ?"
            parametros.append(f"%{fornecedor_nome}%")
        if qualidade:
            query += " AND L.Qualidade = ?"
            parametros.append(qualidade)
        if status:
            query += " AND L.StatusLote = ?"
            parametros.append(status)
        if apenas_com_residuos:
            query += " AND L.QuantidadeSacas > 0 AND L.QuantidadeSacas <= 0.01"            
        
        query += " ORDER BY L.CodigoLote, HL.DataMovimento ASC"
        
        cursor.execute(query, parametros)
        linhas = cursor.fetchall()
        
        # ---Agrupamento em Dicionário (Master-Detail) ---
        lotes_agrupados = {}
        
        for row in linhas:
            codigo = row.CodigoLote
            
            # Se é a primeira vez que vemos o lote, criamos a capa
            if codigo not in lotes_agrupados:
                lotes_agrupados[codigo] = {
                    "CodigoLote": codigo,
                    "Fornecedor": row.Fornecedor,
                    "Qualidade": row.Qualidade,
                    "StatusLote": row.StatusLote,
                    "QuantidadeOriginal": float(row.QuantidadeOriginal),
                    "SaldoAtual": float(row.SaldoAtual),
                    "Movimentacoes": [] # Lista vazia para receber as linhas do histórico
                }
            
            # Adiciona a movimentação na lista interna do lote (se houver histórico)
            if row.TipoMovimento:
                lotes_agrupados[codigo]["Movimentacoes"].append({
                    "Tipo": row.TipoMovimento,
                    "Data": row.DataMovimento.strftime("%Y-%m-%d %H:%M:%S") if row.DataMovimento else None,
                    "Quantidade": float(row.QuantidadeMovimento)
                })
                
        if not lotes_agrupados:
            return {"mensagem": "Nenhum lote encontrado com os filtros informados."}
            
        # Retorna apenas os valores do dicionário (que será uma Lista limpa de Lotes)
        return {"lotes_encontrados": list(lotes_agrupados.values())}
        
    except Exception as e:
        print(f"\n[DEBUG SQL ERROR] Falha no filtro dinâmico: {str(e)}\n")
        return {"erro": f"Erro interno na consulta SQL: {str(e)}"}
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
        query = """SELECT FornecedorId, NomeFornecedor, QualidadeCafe, Ativo, Estado 
        FROM Fornecedores WHERE NomeFornecedor LIKE ?"""
        cursor.execute(query, ('%' + nome_fornecedor + '%',))
        row = cursor.fetchone()

        if not row:
            return {"mensagem": f"Fornecedor não encontrado: {nome_fornecedor}"}

        return {
            "fornecedor_id": row.FornecedorId,
            "nome_oficial": row.NomeFornecedor,            
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