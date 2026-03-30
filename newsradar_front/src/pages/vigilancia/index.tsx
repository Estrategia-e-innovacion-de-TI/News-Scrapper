/**
 * Vigilancia Tecnológica — Subscription form.
 * Loads available topics from GET /api/vigilancia/topics,
 * submits subscription via POST /api/vigilancia/subscribe.
 */
import React, { useState, useEffect, FormEvent } from "react";
import {
  fetchTopics,
  subscribe,
  type TopicItem,
  type SubscribeResponse,
} from "@/lib/api";

export default function VigilanciaPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubscribeResponse | null>(null);

  useEffect(() => {
    fetchTopics()
      .then((data) => setTopics(data.topics))
      .catch(() => setError("No se pudieron cargar los temas disponibles."));
  }, []);

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

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: 32 }}>
      <h1>Vigilancia Tecnológica — Suscripciones</h1>

      {result ? (
        <div>
          <p>Suscripción exitosa para {result.email}.</p>
          <p>Temas suscritos: {result.subscribed_groups.join(", ")}</p>
          <button onClick={() => setResult(null)}>Nueva suscripción</button>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <fieldset>
            <legend>Datos del suscriptor</legend>

            <div className="form-grid">
              <div>
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="usuario@empresa.com"
                  required
                />
              </div>

              <div>
                <label htmlFor="name">Nombre</label>
                <input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Nombre completo"
                  required
                />
              </div>
            </div>
          </fieldset>

          <fieldset style={{ marginTop: 16 }}>
            <legend>Temas de interés</legend>
            {topics.length === 0 && <p>Cargando temas...</p>}
            {topics.map((t) => (
              <label key={t.group_id} style={{ display: "block", marginBottom: 4 }}>
                <input
                  type="checkbox"
                  checked={selectedGroups.includes(t.group_id)}
                  onChange={() => toggleGroup(t.group_id)}
                />
                {" "}{t.display_name} ({t.term_count} términos)
              </label>
            ))}
          </fieldset>

          <button type="submit" disabled={loading} style={{ marginTop: 12 }}>
            {loading ? "Suscribiendo..." : "Suscribirse"}
          </button>
        </form>
      )}

      {error && <p style={{ color: "red" }}>{error}</p>}
    </main>
  );
}
