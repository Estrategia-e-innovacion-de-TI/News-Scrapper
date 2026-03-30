/**
 * SubscriptionForm — Self-contained subscription form for Vigilancia Tecnológica.
 *
 * Loads available topics on mount via fetchTopics(), validates required fields
 * (email, name, at least one topic), submits via subscribe(), and shows
 * confirmation with email and subscribed topics on success.
 *
 * Validates: Req 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
 */
import React, { useState, useEffect, useCallback, FormEvent } from "react";
import {
  fetchTopics,
  subscribe,
  type TopicItem,
  type SubscribeResponse,
} from "@/lib/api";

export default function SubscriptionForm() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [topicsLoading, setTopicsLoading] = useState(true);
  const [topicsError, setTopicsError] = useState(false);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubscribeResponse | null>(null);

  const loadTopics = useCallback(async () => {
    setTopicsLoading(true);
    setTopicsError(false);
    setError(null);
    try {
      const data = await fetchTopics();
      setTopics(data.topics);
    } catch {
      setTopicsError(true);
      setError("No se pudieron cargar los temas disponibles.");
    } finally {
      setTopicsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTopics();
  }, [loadTopics]);

  function toggleGroup(groupId: string) {
    setSelectedGroups((prev) =>
      prev.includes(groupId)
        ? prev.filter((g) => g !== groupId)
        : [...prev, groupId]
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !name || selectedGroups.length === 0) {
      setError("Complete todos los campos y seleccione al menos un tema.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await subscribe({ email, name, query_groups: selectedGroups });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setEmail("");
    setName("");
    setSelectedGroups([]);
    setResult(null);
    setError(null);
  }

  // ── Topics loading state ──
  if (topicsLoading) {
    return (
      <div data-testid="subscription-form" aria-label="Formulario de suscripción">
        <p>Cargando temas...</p>
      </div>
    );
  }

  // ── Topics load error with retry ──
  if (topicsError) {
    return (
      <div data-testid="subscription-form" aria-label="Formulario de suscripción">
        <p role="alert" style={{ color: "var(--color-error, red)" }}>
          {error}
        </p>
        <button type="button" onClick={loadTopics}>
          Reintentar
        </button>
      </div>
    );
  }

  // ── Success confirmation ──
  if (result) {
    return (
      <div data-testid="subscription-form" aria-label="Formulario de suscripción">
        <div data-testid="subscription-confirmation">
          <p>Suscripción exitosa para {result.email}.</p>
          <p>Temas suscritos: {result.subscribed_groups.join(", ")}</p>
          <button type="button" onClick={resetForm}>
            Nueva suscripción
          </button>
        </div>
      </div>
    );
  }

  // ── Subscription form ──
  return (
    <div data-testid="subscription-form" aria-label="Formulario de suscripción">
      <form onSubmit={handleSubmit} aria-label="Suscripción a vigilancia tecnológica">
        <fieldset>
          <legend>Datos del suscriptor</legend>

          <div className="form-grid">
            <div>
              <label htmlFor="vigilancia-email">Email</label>
              <input
                id="vigilancia-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="usuario@empresa.com"
                required
              />
            </div>

            <div>
              <label htmlFor="vigilancia-name">Nombre</label>
              <input
                id="vigilancia-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Nombre completo"
                required
              />
            </div>
          </div>
        </fieldset>

        <fieldset style={{ marginTop: "var(--spacing-md, 16px)" }}>
          <legend>Temas de interés</legend>
          {topics.map((t) => (
            <label
              key={t.group_id}
              style={{ display: "block", marginBottom: "var(--spacing-xs, 4px)" }}
            >
              <input
                type="checkbox"
                checked={selectedGroups.includes(t.group_id)}
                onChange={() => toggleGroup(t.group_id)}
                aria-label={t.display_name}
              />
              {" "}{t.display_name} ({t.term_count} términos)
            </label>
          ))}
        </fieldset>

        <button
          type="submit"
          disabled={loading}
          style={{ marginTop: "var(--spacing-md, 12px)" }}
        >
          {loading ? "Suscribiendo..." : "Suscribirse"}
        </button>
      </form>

      {error && (
        <p
          role="alert"
          style={{ color: "var(--color-error, red)", marginTop: "var(--spacing-sm, 8px)" }}
          data-testid="subscription-error"
        >
          {error}
        </p>
      )}
    </div>
  );
}
