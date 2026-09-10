using System.Globalization;
using System.Text;

namespace Avacom.Lms.Core.Models;

/// <summary>
/// Identidad lógica de la persona en el expediente. El prototipo no tiene
/// autenticación (Q-04): el identificador externo se deriva del nombre con el que
/// la persona entra al aula, de forma estable y sin acentos ni espacios.
/// </summary>
public static class Identidad
{
    public static string SlugDe(string nombre)
    {
        var normalizado = (nombre ?? string.Empty).Trim().Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder();
        var guion = false;
        foreach (var c in normalizado)
        {
            var categoria = CharUnicodeInfo.GetUnicodeCategory(c);
            if (categoria == UnicodeCategory.NonSpacingMark) continue;
            if (char.IsLetterOrDigit(c))
            {
                sb.Append(char.ToLowerInvariant(c));
                guion = false;
            }
            else if (!guion && sb.Length > 0)
            {
                sb.Append('-');
                guion = true;
            }
        }
        var slug = sb.ToString().TrimEnd('-');
        return string.IsNullOrEmpty(slug) ? "anonimo" : slug;
    }

    public static string InicialesDe(string nombre)
    {
        var partes = (nombre ?? string.Empty).Split(' ', StringSplitOptions.RemoveEmptyEntries);
        return partes.Length == 0 ? "?" : string.Concat(partes.Take(2).Select(p => char.ToUpperInvariant(p[0])));
    }
}
