import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine


# RECURSO para usar APENAS o modelo em português. Estava com looping infinito de baixar o modelo em inglês, mesmo com a configuração do idioma em pt.
configuracao_nlp = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "pt", "model_name": "pt_core_news_lg"}]
}

# Cria o motor de linguagem personalizado
provedor_nlp = NlpEngineProvider(nlp_configuration=configuracao_nlp)
motor_nlp = provedor_nlp.create_engine()

# 3. Inicializa o Analyzer injetando o nosso motor customizado
analyzer = AnalyzerEngine(
    nlp_engine=motor_nlp, 
    supported_languages=["pt"]
)
# anonymizer = AnonymizerEngine()
#FIM DO RECURSO para usar apenas o modelo em português.

# ==============================================================================
# INJEÇÃO DE REGRA PARA CNPJ (FINE-TUNING)
# ==============================================================================

# Expressão regular (regex) para identificar CNPJ
cnpj_regex = r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"

# Padrão 1: CNPJ formatado pelo usuário (Certeza - Score 1.0)
# Se o usuário colocar ponto, barra e traço, sem dúvida é CNPJ
padrao_formatado = Pattern(name="cnpj_formatado", regex=cnpj_regex, score=1.0)

# # Padrão 2: CNPJ apenas com números (Dúvida - Score 0.5)
# # Se tiver apenas 14 números seguidos, vai depender das palavras de contexto.
regex_numeros = r"\b\d{14}\b"
padrao_numeros = Pattern(name="cnpj_numeros", regex=regex_numeros, score=0.5)

# # padrão de busca dando peso de confiança de 0.5 
# cnpj_pattern = Pattern(name="cnpj_pattern", regex=cnpj_regex, score=0.5) 

cnpj_recognizer = PatternRecognizer(
    supported_entity="BR_CNPJ",
    supported_language="pt",
    patterns=[padrao_formatado, padrao_numeros],
    context=["cnpj","empresa","pessoa jurídica","fornecedor"] #palavras que ajudama a aumentar a precisão se estiverem próximas do CNPJ
    )

analyzer.registry.add_recognizer(cnpj_recognizer) #Injetando o reconhecedor de cnpj personalizado na engine

# ==============================================================================
# INJEÇÃO DE REGRA PARA CPF (FINE-TUNING)
# ==============================================================================
# Regex para identificar CPF (com ou sem pontuação)
cpf_regex = r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"

# Padrão 1: CPF formatado (Score Alto)
padrao_cpf_formatado = Pattern(name="cpf_formatado", regex=cpf_regex, score=1.0)

# Padrão 2: CPF apenas números (Score Médio) - São 11 dígitos exatos
regex_cpf_numeros = r"\b\d{11}\b"
padrao_cpf_numeros = Pattern(name="cpf_numeros", regex=regex_cpf_numeros, score=0.6)

# Cria o reconhecedor de CPF
cpf_recognizer = PatternRecognizer(
    supported_entity="BR_CPF",
    supported_language="pt",
    patterns=[padrao_cpf_formatado, padrao_cpf_numeros],
    context=["cpf", "cliente", "pessoa física", "documento"]
)

# Injeta a inteligência no registro do Presidio
analyzer.registry.add_recognizer(cpf_recognizer)

# ==============================================================================
# LISTA DE NEGAÇÃO PARA CÓDIGOS INTERNOS (FALSO POSITIVO DO RECONHECEDOR PERSON)
# ==============================================================================
# Achado em produção: o modelo de NER em português (spaCy pt_core_news_lg) por vezes
# classifica códigos alfanuméricos internos do domínio (ex: 'L-0007', código de lote)
# como entidade PERSON, mascarando-os antes de chegarem ao LLM. Isso corrompe o
# raciocínio de Tool Calling a jusante (o modelo nunca vê o código real). Como esses
# códigos não são PII, filtramos qualquer resultado do analyzer cujo texto casado
# corresponda a um padrão de identificador interno conhecido, antes de tokenizar.
PADROES_CODIGOS_INTERNOS = [
    re.compile(r"^L-\d+$"),  # Código de lote (ex: 'L-0007')
]

def _eh_codigo_interno(texto: str) -> bool:
    """Verifica se o texto casado é, na verdade, um código interno do domínio
    (não PII), e portanto deve ser ignorado pelo mascaramento."""
    return any(padrao.match(texto) for padrao in PADROES_CODIGOS_INTERNOS)

def gerar_dado_sintetico(entity_type: str, contador: int) -> str:
    """
    Gera um dado falso que mantém a estrutura do dado real,
    para que o LLM consiga realizar o Tool Calling corretamente.
    """
    templates = {
        "PERSON": f"Usuario_{contador}",
        "BR_CPF": f"000.000.000-{contador:02d}",      # Mantém formato de CPF
        "BR_CNPJ": f"00.000.000/0001-{contador:02d}",  # Mantém formato de CNPJ
        "EMAIL_ADDRESS": f"anonimo_{contador}@empresa.com",
        "PHONE_NUMBER": f"1199999{contador:04d}"
    }
    
    # Se o tipo não estiver no mapeamento, volta para o padrão seguro <TIPO>
    return templates.get(entity_type, f"<{entity_type}_{contador}>")

def anonimiza_e_tokeniza(texto_inserido: str):
    """
    Analisa o texto, cria tokens únicos para dados sensíveis e 
    retorna o texto seguro junto com um 'cofre' (dicionário) para reversão.
    """
    if not texto_inserido:
        return texto_inserido, {}

    # 1. Analisa o texto
    resultados = analyzer.analyze(
        text=texto_inserido,
        entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "BR_CPF", "BR_CNPJ"], 
        language="pt"
    )

    # 2. Ordena os resultados de trás para frente
    # Isso é importante para não bagunçar os índices da string ao substituir o texto
    resultados_ordenados = sorted(resultados, key=lambda x: x.start, reverse=True)
    
    texto_seguro = texto_inserido
    cofre_tokens = {}
    contador = 1

    # 3. Cria os Tokens e guarda no cofre
    for res in resultados_ordenados:
        valor_real = texto_inserido[res.start:res.end]

        # Ignora falsos positivos: códigos internos do domínio (ex: código de lote)
        # que o reconhecedor de NER às vezes classifica erroneamente como PERSON.
        if _eh_codigo_interno(valor_real):
            continue

        ##Gera o dado sintético (ex: 00.000.000/0001-01)
        #token = f"<{res.entity_type}_{contador}>"    
        token_sintetico = gerar_dado_sintetico(res.entity_type, contador)
        
        ## Guarda no cofre
        #cofre_tokens[token] = valor_real
        cofre_tokens[token_sintetico] = valor_real
        
        ## Substitui na frase original
        #texto_seguro = texto_seguro[:res.start] + token + texto_seguro[res.end:]
        texto_seguro = texto_seguro[:res.start] + token_sintetico + texto_seguro[res.end:]       
        
        contador += 1

    return texto_seguro, cofre_tokens

# Função auxiliar para os tokens (Reidratação)
def reidratar_texto(texto_da_ia: str, cofre: dict) -> str:
    """
    Substitui os dados sintéticos de volta pelos dados reais 
    antes de retornar ao usuário.
    """
    if not texto_da_ia or not cofre:
        return texto_da_ia
        
    texto_final = texto_da_ia
    for token_sintetico, dado_real in cofre.items():
        texto_final = texto_final.replace(token_sintetico, dado_real)
        
    return texto_final

# Para teste (rodando este arquivo diretamente)
if __name__ == "__main__":
    teste_frase = "Por favor, verifique o fornecedor Wilson, CPF 12345678900 e o CNPJ da empresa filial 12345678000195."
    texto_limpo, cofre = anonimiza_e_tokeniza(teste_frase)
    print("Frase Original:", teste_frase)
    print("Frase Segura  :", texto_limpo)
    print("Cofre Gerado  :", cofre)