window.onCanvasSynced = function (data) {
  const tbody = document.getElementById('audit-table-body');
  if (!tbody) return;
  const tr = document.createElement('tr');
  const tdTime = document.createElement('td');
  tdTime.textContent = data.timestamp;
  const tdHash = document.createElement('td');
  tdHash.className = 'audit-hash-cell';
  tdHash.textContent = data.sha256_payload;
  const tdAct = document.createElement('td');
  const spanAct = document.createElement('span');
  spanAct.className = 'audit-action-badge';
  spanAct.textContent = 'SYNC · Canvas';
  tdAct.appendChild(spanAct);
  const tdPriv = document.createElement('td');
  tdPriv.className = 'audit-verified-cell';
  tdPriv.textContent = '✓ Verified';
  tr.append(tdTime, tdHash, tdAct, tdPriv);
  tbody.insertBefore(tr, tbody.firstChild);
  while (tbody.children.length > 12) {
    tbody.removeChild(tbody.lastChild);
  }
};

