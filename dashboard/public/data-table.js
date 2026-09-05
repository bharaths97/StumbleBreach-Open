// Shared sortable, resizable, reorderable, paginated table. The apply-swaps
// storage names are intentionally retained so its existing session layouts keep
// working while other tools can supply their own storageKey values.
(function (global) {
  var tableSorts = {};
  try { tableSorts = JSON.parse(sessionStorage.getItem('applyTableSorts') || '{}') || {}; } catch (_) { tableSorts = {}; }
  var tablePageSizes = {};
  try { tablePageSizes = JSON.parse(sessionStorage.getItem('applyTablePageSizes') || '{}') || {}; } catch (_) { tablePageSizes = {}; }
  var tablePages = {};

  function pageSize(storageKey) {
    var size = Number(tablePageSizes[storageKey] || 10);
    return [10, 15, 20, 25, 30].includes(size) ? size : 10;
  }

  function sortableColumns(columns) {
    return columns.filter(function (column) { return column.key !== 'select'; });
  }

  function defaultSortKey(columns) {
    var column = columns.find(function (item) { return item.sortable; });
    return column ? column.key : columns[0].key;
  }

  function currentSort(storageKey, columns) {
    return tableSorts[storageKey] || { key: defaultSortKey(columns), direction: 'asc' };
  }

  function valueFor(row, column) {
    return column.sortValue ? column.sortValue(row) : row[column.key];
  }

  function sortedRows(rows, columns, sort) {
    var column = columns.find(function (item) { return item.key === sort.key; });
    if (!column) return rows.slice();
    var multiplier = sort.direction === 'desc' ? -1 : 1;
    return rows.slice().sort(function (a, b) {
      var av = valueFor(a, column);
      var bv = valueFor(b, column);
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * multiplier;
      return String(av == null ? '' : av).localeCompare(String(bv == null ? '' : bv), undefined, { numeric: true, sensitivity: 'base' }) * multiplier;
    });
  }

  function columnLayout(storageKey, columns) {
    var visibleColumns = sortableColumns(columns);
    var fallback = { order: visibleColumns.map(function (column) { return column.key; }), widths: {} };
    var saved = null;
    try { saved = JSON.parse(sessionStorage.getItem('applyTableColumns:' + storageKey) || 'null'); } catch (_) { saved = null; }
    if (!saved || !Array.isArray(saved.order)) return fallback;
    var valid = saved.order.filter(function (key) {
      return visibleColumns.some(function (column) { return column.key === key; });
    });
    visibleColumns.forEach(function (column) {
      if (!valid.includes(column.key)) valid.push(column.key);
    });
    return { order: valid, widths: saved.widths && typeof saved.widths === 'object' ? saved.widths : {} };
  }

  function saveColumnLayout(storageKey, layout) {
    sessionStorage.setItem('applyTableColumns:' + storageKey, JSON.stringify(layout));
  }

  function applyColumnLayout(table, storageKey, columns) {
    var layout = columnLayout(storageKey, columns);
    var orderedKeys = columns.some(function (column) { return column.key === 'select'; }) ? ['select'].concat(layout.order) : layout.order;
    table.querySelectorAll('tr').forEach(function (row) {
      var byKey = new Map(Array.from(row.children).map(function (cell) { return [cell.dataset.column, cell]; }));
      orderedKeys.forEach(function (key) {
        if (byKey.has(key)) row.appendChild(byKey.get(key));
      });
    });
    table.querySelectorAll('[data-column]').forEach(function (cell) {
      var width = layout.widths[cell.dataset.column];
      cell.style.width = width ? width + 'px' : '';
    });
  }

  function requestRender(container, options) {
    if (options.onChange) options.onChange();
    else render(container, options);
  }

  function setTableSort(container, options, key) {
    var current = currentSort(options.storageKey, options.columns);
    tableSorts[options.storageKey] = {
      key: key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    };
    sessionStorage.setItem('applyTableSorts', JSON.stringify(tableSorts));
    tablePages[options.storageKey] = 1;
    requestRender(container, options);
  }

  function addColumnControls(table, container, options) {
    var header = table.querySelector('thead tr');
    if (!header) return;
    header.querySelectorAll('th[data-column]').forEach(function (th) {
      if (th.dataset.column === 'select' || th.querySelector('.column-resizer')) return;
      var handle = document.createElement('span');
      handle.className = 'column-resizer';
      handle.title = 'Drag to resize column';
      handle.addEventListener('mousedown', function (event) {
        event.preventDefault();
        handle.classList.add('dragging');
        var startX = event.clientX;
        var startWidth = th.getBoundingClientRect().width;
        var move = function (moveEvent) {
          var width = Math.max(80, Math.min(500, startWidth + moveEvent.clientX - startX));
          table.querySelectorAll('[data-column="' + th.dataset.column + '"]').forEach(function (cell) { cell.style.width = width + 'px'; });
        };
        var stop = function () {
          var layout = columnLayout(options.storageKey, options.columns);
          layout.widths[th.dataset.column] = Math.round(th.getBoundingClientRect().width);
          saveColumnLayout(options.storageKey, layout);
          handle.classList.remove('dragging');
          document.removeEventListener('mousemove', move);
          document.removeEventListener('mouseup', stop);
        };
        document.addEventListener('mousemove', move);
        document.addEventListener('mouseup', stop, { once: true });
      });
      th.appendChild(handle);
    });

    var draggedKey = null;
    header.querySelectorAll('th[data-column]').forEach(function (th) {
      if (th.dataset.column === 'select') return;
      th.draggable = true;
      th.title = 'Drag header to reorder; drag the right edge to resize';
      var moved = false;
      th.addEventListener('click', function (event) {
        if (moved || event.target.closest('.column-resizer') || event.target.closest('.sort-button')) return;
        setTableSort(container, options, th.dataset.column);
      });
      th.addEventListener('dragstart', function (event) {
        draggedKey = th.dataset.column;
        moved = false;
        th.classList.add('column-dragging');
        event.dataTransfer.effectAllowed = 'move';
      });
      th.addEventListener('dragend', function () {
        draggedKey = null;
        header.querySelectorAll('.column-drop-target').forEach(function (cell) { cell.classList.remove('column-drop-target'); });
        th.classList.remove('column-dragging');
        setTimeout(function () { moved = false; }, 0);
      });
      th.addEventListener('dragover', function (event) {
        if (draggedKey && draggedKey !== th.dataset.column) {
          event.preventDefault();
          moved = true;
          th.classList.add('column-drop-target');
        }
      });
      th.addEventListener('dragleave', function () { th.classList.remove('column-drop-target'); });
      th.addEventListener('drop', function (event) {
        event.preventDefault();
        th.classList.remove('column-drop-target');
        if (!draggedKey || draggedKey === th.dataset.column) return;
        var layout = columnLayout(options.storageKey, options.columns);
        var from = layout.order.indexOf(draggedKey);
        var to = layout.order.indexOf(th.dataset.column);
        if (from < 0 || to < 0) return;
        layout.order.splice(from, 1);
        layout.order.splice(to, 0, draggedKey);
        saveColumnLayout(options.storageKey, layout);
        requestRender(container, options);
      });
    });
  }

  function renderPagination(container, options, total) {
    var storageKey = options.storageKey;
    var size = pageSize(storageKey);
    var pageCount = Math.max(1, Math.ceil(total / size));
    var page = Math.min(Math.max(Number(tablePages[storageKey] || 1), 1), pageCount);
    tablePages[storageKey] = page;
    var wrap = document.createElement('div');
    wrap.className = 'table-pagination';
    var label = document.createElement('span');
    label.className = 'muted';
    label.textContent = '> ./page --current=' + page + ' --total=' + pageCount;
    var pageSizeLabel = document.createElement('label');
    pageSizeLabel.className = 'muted';
    pageSizeLabel.textContent = '> ./rows:';
    var select = document.createElement('select');
    [10, 15, 20, 25, 30].forEach(function (value) {
      var option = document.createElement('option');
      option.value = String(value);
      option.textContent = String(value);
      option.selected = value === size;
      select.appendChild(option);
    });
    select.addEventListener('change', function () {
      tablePageSizes[storageKey] = Number(select.value);
      tablePages[storageKey] = 1;
      sessionStorage.setItem('applyTablePageSizes', JSON.stringify(tablePageSizes));
      requestRender(container, options);
    });
    var previous = document.createElement('button');
    previous.type = 'button';
    previous.className = 'secondary';
    previous.textContent = '> ./prev';
    previous.disabled = page <= 1;
    previous.addEventListener('click', function () {
      tablePages[storageKey] = page - 1;
      requestRender(container, options);
    });
    var next = document.createElement('button');
    next.type = 'button';
    next.className = 'secondary';
    next.textContent = '> ./next';
    next.disabled = page >= pageCount;
    next.addEventListener('click', function () {
      tablePages[storageKey] = page + 1;
      requestRender(container, options);
    });
    pageSizeLabel.appendChild(select);
    wrap.append(label, pageSizeLabel, previous, next);
    return { element: wrap, page: page, size: size };
  }

  function render(container, options) {
    var columns = options.columns || [];
    var sort = currentSort(options.storageKey, columns);
    var sorted = sortedRows(options.rows || [], columns, sort);
    var size = pageSize(options.storageKey);
    var pageCount = Math.max(1, Math.ceil(sorted.length / size));
    var page = Math.min(Math.max(Number(tablePages[options.storageKey] || 1), 1), pageCount);
    tablePages[options.storageKey] = page;
    var pageRows = sorted.slice((page - 1) * size, page * size);

    container.innerHTML = '';
    var table = document.createElement('table');
    table.className = 'data-table';
    table.dataset.dataTable = 'true';
    var thead = document.createElement('thead');
    var header = document.createElement('tr');
    columns.forEach(function (column) {
      var th = document.createElement('th');
      th.dataset.column = column.key;
      if (column.className) th.className = column.className;
      if (column.sortable) {
        th.dataset.sortKey = column.key;
        var indicator = sort.key === column.key ? (sort.direction === 'asc' ? ' ▲' : ' ▼') : '';
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'sort-button';
        button.textContent = column.label + indicator;
        button.title = 'Sort by ' + column.label;
        button.addEventListener('click', function () { setTableSort(container, options, column.key); });
        th.appendChild(button);
      } else {
        th.textContent = column.label || '';
      }
      header.appendChild(th);
    });
    thead.appendChild(header);
    table.appendChild(thead);
    var tbody = document.createElement('tbody');
    pageRows.forEach(function (row) { tbody.appendChild(options.renderRow(row)); });
    table.appendChild(tbody);
    applyColumnLayout(table, options.storageKey, columns);
    addColumnControls(table, container, options);
    var tableWrap = document.createElement('div');
    tableWrap.className = 'table-wrap';
    tableWrap.appendChild(table);
    container.appendChild(tableWrap);
    container.appendChild(renderPagination(container, options, sorted.length).element);
    return { table: table, pageRows: pageRows, sortedRows: sorted };
  }

  global.DataTable = { render: render };
})(window);
