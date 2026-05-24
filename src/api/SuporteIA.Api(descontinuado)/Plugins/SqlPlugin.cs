namespace SuporteIA.Api.Plugins; 
using System.ComponentModel;
using Microsoft.Data.SqlClient;
using Microsoft.SemanticKernel;
using Microsoft.Extensions.Configuration;

public class SqlPlugin
{
    private readonly string _connectionString;

    public SqlPlugin(IConfiguration configuration)
    {
        // Pega a string que configuramos no appsettings
        _connectionString = configuration.GetConnectionString("DefaultConnection");
    }

    [KernelFunction, Description("Verifica o status atual e o histórico de movimentos de um lote específico no banco de dados.")]
    public async Task<string> GetLoteStatus(
        [Description("O código do lote, ex: LOTE-202")] string codigoLote)
    {
        using var conn = new SqlConnection(_connectionString);
        await conn.OpenAsync();

        // Consulta que traz o lote e seus movimentos concatenados
        var sql = @"
            SELECT L.CodigoLote, L.QuantidadeSacas, L.StatusLote,
                   (SELECT STRING_AGG(TipoMovimento, ', ') FROM MovimentacaoLotes WHERE LoteId = L.Id) as Movimentos
            FROM Lotes L
            WHERE L.CodigoLote = @codigo";

        using var cmd = new SqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("@codigo", codigoLote);

        using var reader = await cmd.ExecuteReaderAsync();
        if (await reader.ReadAsync())
        {
            var qtd = reader["QuantidadeSacas"];
            var status = reader["StatusLote"];
            var movs = reader["Movimentos"]?.ToString() ?? "Nenhum movimento encontrado";

            return $"Lote: {codigoLote} | Saldo: {qtd} sacas | Status: {status} | Movimentos registrados: {movs}";
        }

        return "Lote não encontrado no banco de dados.";
    }

    [KernelFunction, Description("Zera saldos residuais insignificantes (menores que 0.001) para correção de inventário.")]
    public async Task<string> ZerarSaldoResidual(
        [Description("O código do lote a ser ajustado")] string codigoLote)
    {
        using var conn = new SqlConnection(_connectionString);
        await conn.OpenAsync();

        // Segurança: só zera se for realmente um resíduo minúsculo
        var sql = "UPDATE Lotes SET QuantidadeSacas = 0, StatusLote = 'Esgotado' " +
                  "WHERE CodigoLote = @codigo AND QuantidadeSacas > 0 AND QuantidadeSacas < 0.001";

        using var cmd = new SqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("@codigo", codigoLote);

        int rows = await cmd.ExecuteNonQueryAsync();

        return rows > 0 
            ? $"Sucesso: O saldo residual do lote {codigoLote} foi zerado e o status alterado para Esgotado." 
            : $"Ajuste não realizado. Verifique se o lote {codigoLote} possui saldo superior ao limite de tolerância (0.001).";
    }
}