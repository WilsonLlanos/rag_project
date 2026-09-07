#!/usr/bin/env bash
# Localiza, no PDF compilado do TCC, as páginas que contêm um termo e as
# rasteriza em PNG para inspeção visual (conferir figuras/layout).
#
# Uso: bash ver_pagina.sh <termo> <dir_saida> [caminho_para_docs]
#   termo               Texto que aparece na página-alvo (ex.: trecho do \caption)
#   dir_saida           Onde salvar os PNGs (use o scratchpad da sessão)
#   caminho_para_docs   Diretório docs/ do projeto (padrão: "docs")
set -euo pipefail

TERMO="${1:?uso: ver_pagina.sh <termo> <dir_saida> [docs_dir]}"
OUT_DIR="${2:?uso: ver_pagina.sh <termo> <dir_saida> [docs_dir]}"
DOCS_DIR="${3:-docs}"
PDF="USPSC-modelo-ICMC-PORTUGUÊS.pdf"

cd "$DOCS_DIR"
mkdir -p "$OUT_DIR"

if [ ! -f "$PDF" ]; then
    echo "PDF '$PDF' não encontrado em $(pwd) — rode verificar_build.sh primeiro."
    exit 1
fi

PAGINAS=$(pdftotext "$PDF" - 2>/dev/null | awk -v RS='\f' -v termo="$TERMO" 'index($0, termo){print NR}')

if [ -z "$PAGINAS" ]; then
    echo "Termo '$TERMO' não encontrado em nenhuma página do PDF."
    exit 1
fi

echo "Páginas encontradas: $PAGINAS"
for p in $PAGINAS; do
    pdftoppm -png -r 130 -f "$p" -l "$p" "$PDF" "$OUT_DIR/pg"
done
echo "PNGs salvos em $OUT_DIR (leia com a ferramenta Read)"
