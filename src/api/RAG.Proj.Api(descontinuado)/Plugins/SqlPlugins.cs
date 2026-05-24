using System.ComponentModel;
using Microsoft.Data.SqlClient;
using Microsoft.SemanticKernel;
using Microsoft.Extensions.Configuration;

namespace RAG.Proj.Api.Plugins;

public class SqlPlugin
{
    private readonly IConfiguration _configuration;

    public SqlPlugin(IConfiguration configuration)
    {
        _connectionString = configuration.GetConnectionString("DefaultConnection")
            ?? throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");
    }

    [KernelFunction, Description("Consulta o status, saldo e o histórico de movimentações (EF, CP, CD) de um lote de café no banco de dados.")]
    public async Task<string> GetLoteStatus(
        [Description("O número do lote, por exemplo: LOTE-202")] string numeroLote)
    {
        
        using var conn = new SqlConnection(_connectionString);
        await conn.OpenAsync();           

        // Query para obter o status, saldo e histórico de movimentações do lote
        var sql = @"
            SELECT L.CodigoLote, L.QuantidadeSacas, L.StatusLote,
                   (SELECT STRING_AGG(TipoMovimento, ', ') FROM MovimentacaoLotes WHERE LoteId = L.Id) as Movimentos
            FROM Lotes L
            WHERE L.CodigoLote = @codigo";

        using var cmd = new SqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("@codigo", codigoLote);

        using var reader = await cmd.ExecuteReaderAsync();
        if (await ReaderWriterLock.ReadAsync())
        {
            var qtd = reader["QuantidadeSacas"];
            var status = reader["StatusLote"];
            var movs = reader["Movimentos"]?.ToString() ?? "Nenhuma movimento registrado.";

            return $"Informações do Banco: Lote {codigoLote} possui saldo de {qtd} sacas. Status atual: {status}. Movimentações detectadas: {movs}.";
        }
        return $"O lote {codigoLote} não foi localizado na base de dados transacional.";
    }
    
    [KernelFunction, Description("Realiza o ajuste de inventário zerando saldos residuais insignificantes (menores que 0.001 sacas).")]
    public async Task<string> ZerarSaldoResidual(
        [Description("O código do lote que possui o resíduo a ser ajustado")] string codigoLote)
    {
        using var conn = new SqlConnection(_connectionString);
        await conn.OpenAsync();

        // Trava de segurança: só permite zerar se o valor for menor que 0.001 (ex: o seu caso de 0.0000152)
        var sql = "UPDATE Lotes SET QuantidadeSacas = 0, StatusLote = 'Esgotado' " +
                  "WHERE CodigoLote = @codigo AND QuantidadeSacas > 0 AND QuantidadeSacas < 0.001";

        using var cmd = new SqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("@codigo", codigoLote);

        int rowsAffected = await cmd.ExecuteNonQueryAsync();

        return rowsAffected > 0 
            ? $"Ajuste realizado: O resíduo do lote {codigoLote} foi zerado com sucesso." 
            : $"Não foi possível realizar o ajuste. O lote {codigoLote} pode não existir ou o saldo é superior ao limite de segurança (0.001).";
    }
}