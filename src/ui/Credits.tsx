import { useAppStore } from "../store";

/**
 * Attribution screen. The 3D geometry is derived from open-source anatomy under
 * CC BY-SA, which requires visible attribution. The exact text is also emitted by
 * the asset pipeline into ATTRIBUTION.md; keep the two in sync.
 */
export function Credits() {
  const open = useAppStore((s) => s.creditsOpen);
  const toggle = useAppStore((s) => s.toggleCredits);
  if (!open) return null;

  return (
    <div className="credits-overlay" onClick={() => toggle(false)}>
      <div className="credits panel" onClick={(e) => e.stopPropagation()}>
        <h2>Credits &amp; Attribution</h2>
        <p>
          3D anatomy geometry in this application is derived from open-source datasets and is used
          under their respective licenses. No proprietary or SaaS anatomy service is used.
        </p>

        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 16, marginBottom: 4 }}>Geometry — BodyParts3D</h3>
        <pre>
{`BodyParts3D, © The Database Center for Life Science,
licensed under CC BY-SA 2.1 Japan.
Source: https://lifesciencedb.jp/bp3d/
Geometry has been grouped, decimated and re-exported for web rendering;
these modifications are likewise distributed under CC BY-SA 2.1 Japan.`}
        </pre>

        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 16, marginBottom: 4 }}>Naming reference — Z-Anatomy</h3>
        <pre>
{`Structure naming and system grouping informed by Z-Anatomy,
licensed under CC BY-SA 4.0.
Source: https://www.z-anatomy.com/
Used as a naming/grouping reference only; no Z-Anatomy geometry or
bundled non-commercial add-ons are included.`}
        </pre>

        <p style={{ marginTop: 14 }}>
          The application code is proprietary. Only the model files and edits to them carry the
          CC BY-SA obligation. See <code>asset-pipeline/LICENSE-AUDIT.md</code> for the per-structure audit.
        </p>
        <button className="icon-btn" style={{ marginTop: 8 }} onClick={() => toggle(false)}>Close</button>
      </div>
    </div>
  );
}
