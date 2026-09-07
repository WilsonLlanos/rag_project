#!/usr/bin/env bash
# Compila o TCC (USPSC/abnTeX2) e reporta citações/referências indefinidas.
#
# Uso: bash verificar_build.sh [caminho_para_docs]
#   caminho_para_docs  Diretório docs/ do projeto (padrão: "docs")
#
# Sai com código != 0 se a compilação falhar. Sempre imprime o resumo de
# citações/referências indefinidas, mesmo quando a compilação é bem-sucedida,
# porque o BibTeX pode reportar "undefined" sem quebrar o build.
set -euo pipefail

DOCS_DIR="${1:-docs}"
MAIN_TEX="USPSC-modelo-ICMC-PORTUGUÊS.tex"
LOG_FILE="${MAIN_TEX%.tex}.log"

cd "$DOCS_DIR"

echo "--- Compilando $MAIN_TEX em $(pwd) ---"
if latexmk -pdf -interaction=nonstopmode -halt-on-error "$MAIN_TEX" > build.log 2>&1; then
    BUILD_OK=1
else
    BUILD_OK=0
fi

echo "--- Citações/referências indefinidas ---"
if [ -f "$LOG_FILE" ]; then
    if grep -iE "undefined (citation|reference)|Citation .* undefined|Reference .* undefined" "$LOG_FILE"; then
        echo "^ AVISOS ACIMA precisam ser corrigidos (chave de \\cite ou \\label/\\ref errada)."
    else
        echo "Nenhuma encontrada."
    fi
else
    echo "Log '$LOG_FILE' não encontrado — a compilação pode ter falhado antes de gerá-lo."
fi

if [ "$BUILD_OK" -eq 0 ]; then
    echo "--- ERRO na compilação — últimas linhas de build.log ---"
    tail -60 build.log
    exit 1
fi

echo "--- Compilação OK ---"
