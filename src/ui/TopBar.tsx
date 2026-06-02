import { useAppStore } from "../store";
import { usePresenter } from "../presenter/usePresenter";
import { MOCK_MEMBERS, MOCK_MEMBER_ORDER } from "../data/mock/members";
import { activeDataSource } from "../data/loadScreening";

export function TopBar() {
  const presenter = usePresenter("wall");
  const payload = useAppStore((s) => s.payload);
  const toggleCredits = useAppStore((s) => s.toggleCredits);
  const toggleBodyFit = useAppStore((s) => s.toggleBodyFit);

  return (
    <div className="topbar">
      <div className="brand">
        <span className="mark">Acko Clinic</span>
        <span className="sub">Post-screening body consultation</span>
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div className="member-chip panel">
          <div>
            <div className="name">{payload?.member.name ?? "—"}</div>
            <div className="meta">
              {payload ? `${payload.member.age}y · ${payload.member.sex} · screened ${payload.member.screenedAt}` : ""}
            </div>
          </div>
          {activeDataSource === "mock" && (
            <select
              value={payload?.member.id ?? ""}
              onChange={(e) => presenter.loadMember(e.target.value)}
              aria-label="Switch member"
            >
              {MOCK_MEMBER_ORDER.map((id) => (
                <option key={id} value={id}>{MOCK_MEMBERS[id].member.name}</option>
              ))}
            </select>
          )}
        </div>
        <button className="icon-btn" onClick={() => toggleBodyFit(true)}>Body fit</button>
        <button className="icon-btn" onClick={() => toggleCredits(true)}>Credits</button>
      </div>
    </div>
  );
}
