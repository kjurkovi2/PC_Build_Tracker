const API = "/api";
let trenutniBuildId = null;
let trenutniBuild = null;

const euro = (n) =>
  Number(n).toLocaleString("hr-HR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";

async function ucitajKategorije() {
  const odgovor = await fetch(`${API}/kategorije`);
  const kategorije = await odgovor.json();
  const select = document.getElementById("komponenta-kategorija");
  select.innerHTML = kategorije.map((k) => `<option value="${k}">${k}</option>`).join("");
}

async function ucitajBuildove() {
  const odgovor = await fetch(`${API}/buildovi`);
  const buildovi = await odgovor.json();

  document.getElementById("broj-buildova").textContent = buildovi.length;
  const lista = document.getElementById("lista-buildova");

  if (buildovi.length === 0) {
    lista.innerHTML = `<li class="list-group-item text-muted">Još nema buildova.</li>`;
    return;
  }

  lista.innerHTML = buildovi
    .map(
      (b) => `
      <li class="list-group-item ${b.id === trenutniBuildId ? "active" : ""}" data-id="${b.id}">
        <div class="d-flex justify-content-between">
          <span>${b.naziv}</span>
          <strong>${euro(b.ukupna_cijena)}</strong>
        </div>
        <small>${b.broj_komponenti} komponenti</small>
      </li>`
    )
    .join("");

  lista.querySelectorAll("li[data-id]").forEach((li) => {
    li.addEventListener("click", () => odaberiBuild(Number(li.dataset.id)));
  });
}

async function odaberiBuild(id) {
  trenutniBuildId = id;
   document.getElementById("uredi-build-forma").classList.add("d-none");
  document.getElementById("prazno-stanje").classList.add("d-none");
  document.getElementById("detalji-builda").classList.remove("d-none");

  const odgovor = await fetch(`${API}/buildovi/${id}`);
  if (!odgovor.ok) {
    trenutniBuildId = null;
    document.getElementById("detalji-builda").classList.add("d-none");
    document.getElementById("prazno-stanje").classList.remove("d-none");
    return;
  }
  const build = await odgovor.json();
    trenutniBuild = build;

  document.getElementById("detalj-naziv").textContent = build.naziv;
  document.getElementById("detalj-opis").textContent = build.opis || "(bez opisa)";
  document.getElementById("detalj-ukupno").textContent = euro(build.ukupna_cijena);

  const redovi = document.getElementById("redovi-komponenti");
  if (build.komponente.length === 0) {
    redovi.innerHTML = `<tr><td colspan="5" class="text-muted text-center">Još nema dodanih komponenti.</td></tr>`;
  } else {
    redovi.innerHTML = build.komponente
      .map(
        (k) => `
        <tr data-id="${k.id}">
          <td>${k.naziv}</td>
          <td><span class="badge text-bg-light border">${k.kategorija}</span></td>
          <td>${k.proizvodac || "-"}</td>
          <td class="text-end">${euro(k.cijena)}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-danger obrisi-komponentu-btn">✕</button>
          </td>
        </tr>`
      )
      .join("");

    redovi.querySelectorAll(".obrisi-komponentu-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const komponentaId = e.target.closest("tr").dataset.id;
        await fetch(`${API}/komponente/${komponentaId}`, { method: "DELETE" });
        await odaberiBuild(trenutniBuildId);
        await ucitajBuildove();
      });
    });
  }

  await ucitajBuildove();
}

document.getElementById("build-forma").addEventListener("submit", async (e) => {
  e.preventDefault();
  const naziv = document.getElementById("build-naziv").value.trim();
  const opis = document.getElementById("build-opis").value.trim();
  if (!naziv) return;

  const odgovor = await fetch(`${API}/buildovi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ naziv, opis }),
  });
  if (odgovor.ok) {
    const build = await odgovor.json();
    e.target.reset();
    await ucitajBuildove();
    await odaberiBuild(build.id);
  } else {
    const greska = await odgovor.json();
    alert(greska.error);
  }
});

document.getElementById("komponenta-forma").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!trenutniBuildId) return;

  const podaci = {
    naziv: document.getElementById("komponenta-naziv").value.trim(),
    kategorija: document.getElementById("komponenta-kategorija").value,
    proizvodac: document.getElementById("komponenta-proizvodac").value.trim(),
    cijena: document.getElementById("komponenta-cijena").value,
  };

  const odgovor = await fetch(`${API}/buildovi/${trenutniBuildId}/komponente`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(podaci),
  });
  if (odgovor.ok) {
    e.target.reset();
    await odaberiBuild(trenutniBuildId);
  } else {
    const greska = await odgovor.json();
    alert(greska.error);
  }
});

document.getElementById("obrisi-build-btn").addEventListener("click", async () => {
  if (!trenutniBuildId) return;
  if (!confirm("Obrisati ovaj build i sve njegove komponente?")) return;

  await fetch(`${API}/buildovi/${trenutniBuildId}`, { method: "DELETE" });
  trenutniBuildId = null;
  document.getElementById("detalji-builda").classList.add("d-none");
  document.getElementById("prazno-stanje").classList.remove("d-none");
  await ucitajBuildove();
});

document.getElementById("uredi-build-btn").addEventListener("click", () => {
  if (!trenutniBuild) return;
  document.getElementById("uredi-build-naziv").value = trenutniBuild.naziv;
  document.getElementById("uredi-build-opis").value = trenutniBuild.opis || "";
  document.getElementById("uredi-build-forma").classList.remove("d-none");
});

document.getElementById("odustani-uredi-btn").addEventListener("click", () => {
  document.getElementById("uredi-build-forma").classList.add("d-none");
});

document.getElementById("uredi-build-forma").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!trenutniBuildId) return;

  const naziv = document.getElementById("uredi-build-naziv").value.trim();
  const opis = document.getElementById("uredi-build-opis").value.trim();
  if (!naziv) return;

  const odgovor = await fetch(`${API}/buildovi/${trenutniBuildId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ naziv, opis }),
  });
  if (odgovor.ok) {
    document.getElementById("uredi-build-forma").classList.add("d-none");
    await odaberiBuild(trenutniBuildId);
    await ucitajBuildove();
  } else {
    const greska = await odgovor.json();
    alert(greska.error);
  }
});

(async function init() {
  await ucitajKategorije();
  await ucitajBuildove();
})();