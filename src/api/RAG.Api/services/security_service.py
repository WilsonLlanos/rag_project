from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider 
from presidio_anonymizer import AnonymizerEngine

# 1. Configuração Estrita: Sobrescrevendo o padrão do Presidio
# RECURSO para usar APENAS o modelo em português que já baixamos. Estava com looping infinito de baixar o modelo em inglês, mesmo com a configuração do idioma em pt.
configuracao_nlp = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "pt", "model_name": "pt_core_news_lg"}]
}

# 2. Cria o motor de linguagem personalizado
provedor_nlp = NlpEngineProvider(nlp_configuration=configuracao_nlp)
motor_nlp = provedor_nlp.create_engine()

# 3. Inicializa o Analyzer injetando o nosso motor customizado
analyzer = AnalyzerEngine(
    nlp_engine=motor_nlp, 
    supported_languages=["pt"]
)
anonymizer = AnonymizerEngine()
#FIM DO RECURSO para usar apenas o modelo em português.


# Expressão regular (regex) para identificar CNPJ
cnpj_regex = r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"

# Padrão 1: CNPJ formatado pelo usuário (Certeza - Score 1.0)
# Se o usuário colocar ponto, barra e traço, sem dúvida é CNPJ
padrao_formatado = Pattern(name="cnpj_formatado", regex=cnpj_regex, score=1.0)

# Padrão 2: CNPJ apenas com números (Dúvida - Score 0.5)
# Se tiver apenas 14 números seguidos, vai depender das palavras de contexto.
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

# # modelo em português
# analyzer = AnalyzerEngine(supported_languages=["pt"])
# anonymizer = AnonymizerEngine()

analyzer.registry.add_recognizer(cnpj_recognizer) #Injetando o reconhecedor de cnpj personalizado na engine

def anonimiza_texto(texto_inserido: str):
    # analisa o texto e identifica as entidades
    resultados = analyzer.analyze(
        text=texto_inserido,
        entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "BR_CPF", "BR_CNPJ"], 
        language="pt")

    # anonimiza o texto usando as entidades identificadas
    texto_anonimizado = anonymizer.anonymize(text=texto_inserido, analyzer_results=resultados)

    return texto_anonimizado.text