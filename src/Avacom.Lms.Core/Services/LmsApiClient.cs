using System.Net.Http.Json;
using Avacom.Lms.Core.Models;

namespace Avacom.Lms.Core.Services;

public interface ILmsApiClient
{
    Task<bool> CheckHealthAsync(Uri baseUri, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<Course>> GetCoursesAsync(Uri baseUri, string studentId, CancellationToken cancellationToken = default);
    Task SubmitAnswerAsync(Uri baseUri, string attemptId, string questionId, string optionId, CancellationToken cancellationToken = default);
}

public sealed class LmsApiClient(HttpClient httpClient) : ILmsApiClient
{
    public async Task<bool> CheckHealthAsync(Uri baseUri, CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await httpClient.GetAsync(new Uri(baseUri, "health/"), cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch (HttpRequestException)
        {
            return false;
        }
        catch (TaskCanceledException)
        {
            return false;
        }
    }

    public async Task<IReadOnlyList<Course>> GetCoursesAsync(Uri baseUri, string studentId, CancellationToken cancellationToken = default)
    {
        var uri = new Uri(baseUri, $"api/students/{Uri.EscapeDataString(studentId)}/courses/");
        return await httpClient.GetFromJsonAsync<List<Course>>(uri, cancellationToken) ?? [];
    }

    public async Task SubmitAnswerAsync(Uri baseUri, string attemptId, string questionId, string optionId, CancellationToken cancellationToken = default)
    {
        var payload = new { attempt_id = attemptId, question_id = questionId, option_id = optionId, client_event_id = Guid.NewGuid().ToString("N") };
        using var response = await httpClient.PostAsJsonAsync(new Uri(baseUri, "api/quiz-attempts/answer/"), payload, cancellationToken);
        response.EnsureSuccessStatusCode();
    }
}

