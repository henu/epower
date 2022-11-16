UI = {};

UI.nodes_from_server = {};
UI.connections_from_server = {};
UI.nodes = {};
UI.connections = {};
UI.settings = {};
UI.static_data = {};

function stripTags(str)
{
    return ('' + str).replace(/<\/?[^>]+(>|$)/g, '');
}

function escapeDoubleQuotes(str)
{
    return ('' + str).replace(/"/g, '&quot;');
}

function fetchStaticData(urls_and_names)
{
    return new Promise(function(resolve, reject) {
        const url_and_name = urls_and_names[0];
        urls_and_names = urls_and_names.slice(1);
        $.ajax({
            url: url_and_name[0],
        }).then(
            function(data, text_status, request) {
                UI.static_data[url_and_name[1]] = data;
                if (urls_and_names.length > 0) {
                    fetchStaticData(urls_and_names).then(resolve, reject);
                } else {
                    resolve();
                }
            },
            function(request, text_status, error_thrown) {
                reject();
            },
        );
    });
}

function saveVariables(vars)
{
    return new Promise(function(resolve, reject) {
        // Pick one key/variable pair
        const name = Object.keys(vars)[0];
        const value = vars[name];
        delete vars[name];
        $.ajax({
            url: '/api/v1/variables/',
            method: 'POST',
            headers: {'X-CSRFToken': window.csrf_token},
            data: JSON.stringify({
                'name': name,
                'value': value,
            }),
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
        }).then(
            function(data, text_status, request) {
                if (Object.keys(vars).length > 0) {
                    saveVariables(vars).then(
                        function() {
                            resolve();
                        },
                        function() {
                            reject();
                        },
                    );
                } else {
                    resolve();
                }
            },
            function(request, text_status, error_thrown) {
                // In case the object already exists, try to update it
                $.ajax({
                    url: '/api/v1/variables/' + name + '/',
                    method: 'PATCH',
                    headers: {'X-CSRFToken': window.csrf_token},
                    data: JSON.stringify({
                        'value': value,
                    }),
                    dataType: 'json',
                    contentType: 'application/json; charset=utf-8',
                }).then(
                    function(data, text_status, request) {
                        if (Object.keys(vars).length > 0) {
                            saveVariables(vars).then(
                                function() {
                                    resolve();
                                },
                                function() {
                                    reject();
                                },
                            );
                        } else {
                            resolve();
                        }
                    },
                    function(request, text_status, error_thrown) {
                        reject();
                    },
                );
            },
        );
    });
}

function setNodeDetailsModelEnabled(settings_fields, enabled)
{
    $('#node_edit_input_name').prop('disabled', !enabled);
    for (var [key, field] of Object.entries(settings_fields)) {
        $('#node_edit_input_settings_' + key).prop('disabled', !enabled);
    }
    $('#node_edit_button_cancel').prop('disabled', !enabled);
    $('#node_edit_button_proceed').prop('disabled', !enabled);
}

function generateNodeDetailsFormHtml(logic_class, node)
{
    const settings_fields = UI.static_data.logics[logic_class].settings_fields;

    if (node) {
        var node_name = node['name'];
        var node_settings = node['settings'];
    } else {
        var node_name = '';
        var node_settings = {};
    }

    var settings_inputs = '';
    for (var [key, field] of Object.entries(settings_fields)) {
        settings_inputs += '<div class="form-group">';
        settings_inputs += '<label for="node_edit_input_settings_' + key + '" class="col-form-label">' + field['label'] + '</label>';
        if (field['type'] == 'string') {
            settings_inputs += '<input type="text" class="form-control" id="node_edit_input_settings_' + key + '" value="' + escapeDoubleQuotes(stripTags(node_settings[key] ?? '')) + '">';
        } else if (field['type'] == 'password') {
            settings_inputs += '<input type="password" class="form-control" id="node_edit_input_settings_' + key + '" value="' + escapeDoubleQuotes(stripTags(node_settings[key] ?? '')) + '">';
        } else if (field['type'] == 'integer') {
            var min_limit = '';
            if (field['min'] != null) {
                min_limit = ' min="' + field['min'] + '"'
            }
            var max_limit = '';
            if (field['max'] != null) {
                max_limit = ' max="' + field['max'] + '"'
            }
            settings_inputs += '<input id="node_edit_input_settings_' + key + '" type="number" class="form-control" value="' + stripTags(node_settings[key] ?? field['min'] ?? '') + '"' + min_limit + max_limit + '>';
        } else if (field['type'] == 'time') {
            settings_inputs += '<input id="node_edit_input_settings_' + key + '" type="time" class="form-control" value="' + stripTags(node_settings[key] ?? field['min'] ?? '') + '"' + min_limit + max_limit + '>';
        }
        settings_inputs += '</div>';
    }

    return '' +
        '<div class="form-group">' +
            '<label for="node_edit_input_name" class="col-form-label">Name:</label>' +
            '<input id="node_edit_input_name" type="text" class="form-control" value="' + escapeDoubleQuotes(stripTags(node_name)) + '">' +
        '</div>' +
        settings_inputs;
}

function submitNodeDetailsForm(logic_class, node_id)
{
    const settings_fields = UI.static_data.logics[logic_class].settings_fields;

    // Convert form inputs to JSON data for ajax request
    var params = {};
    params['name'] = $('#node_edit_input_name').val();
    params['settings'] = {};
    for (var [key, field] of Object.entries(settings_fields)) {
        var value = $('#node_edit_input_settings_' + key).val();
        if (field['type'] == 'integer') {
            value = Number(value);
        }
        params['settings'][key] = value;
    }
    if (!node_id) {
        params['logic_class'] = logic_class;
        params['pos_x'] = 50;
        params['pos_y'] = 50;
    }

    // Disable form, so user cannot do anything while waiting
    setNodeDetailsModelEnabled(settings_fields, false);

    // Clear all error messages
    $('#node_edit_modal .invalid-feedback').each(function() {
        $(this).remove();
    });
    $('#node_edit_modal input').each(function() {
        $(this).removeClass('is-invalid');
    });

    // Use Ajax to update on server
    var url;
    var method;
    if (node_id) {
        url = '/api/v1/nodes/' + node_id + '/';
        method = 'PATCH';
    } else {
        url = '/api/v1/nodes/';
        method = 'POST';
    }
    $.ajax({
        url: url,
        method: method,
        headers: {'X-CSRFToken': window.csrf_token},
        data: JSON.stringify(params),
        dataType: 'json',
        contentType: 'application/json; charset=utf-8',
    }).then(
        function(data, text_status, request) {
            bootstrap.Modal.getInstance(document.getElementById('node_edit_modal')).hide();
            // Also update to local memory
            if (node_id) {
                UI.nodes[node_id]['name'] = params['name'];
                UI.nodes[node_id]['settings'] = params['settings'];
                UI.nodes_from_server[node_id]['name'] = params['name'];
                UI.nodes_from_server[node_id]['settings'] = params['settings'];
            } else {
                node_id = data['id'];
                UI.nodes[node_id] = data;
                UI.nodes_from_server[node_id] = data;
            }
            reconstructNodesAndConnectionsToUi();
        },
        function(request, text_status, error_thrown) {
            setNodeDetailsModelEnabled(settings_fields, true);
            // Add error messages to fields
            if (request.responseJSON['name']) {
                $('#node_edit_input_name').addClass('is-invalid')
                $('#node_edit_input_name').after($('<div class="invalid-feedback">' + request.responseJSON['name'][0] + '</div>'));
            }
            if (request.responseJSON['settings']) {
                for (var [key, field] of Object.entries(settings_fields)) {
                    if (request.responseJSON['settings'][key]) {
                        $('#node_edit_input_settings_' + key).addClass('is-invalid')
                        $('#node_edit_input_settings_' + key).after($('<div class="invalid-feedback">' + request.responseJSON['settings'][key][0] + '</div>'));
                    }
                }
            }
        },
    );
}

function constructAndShowNodeDetailsModal(node_id)
{
    // Remove possible old modal
    $('#node_edit_modal').remove();

    var node = UI.nodes[node_id];

    const settings_fields = UI.static_data.logics[node.logic_class].settings_fields;

    // Create new modal
    $('#main').append($(
        '<div class="modal fade" tabindex="-1" id="node_edit_modal" data-bs-backdrop="static" data-bs-keyboard="true">' +
            '<div class="modal-dialog">' +
                '<div class="modal-content">' +
                    '<div class="modal-header">' +
                        '<h5 class="modal-title">Edit node "' + node['name'] + '"</h5>' +
                    '</div>' +
                    '<div class="modal-body">' +
                        generateNodeDetailsFormHtml(node.logic_class, node) +
                    '</div>' +
                    '<div class="modal-footer">' +
                        '<button id="node_edit_button_cancel" type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>' +
                        '<button id="node_edit_button_remove" type="button" class="btn btn-danger btn-block">Remove</button>' +
                        '<button id="node_edit_button_proceed" type="button" class="btn btn-primary">Save</button>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>'
    ));

    $('#node_edit_button_proceed').on('click', function() {
        submitNodeDetailsForm(node.logic_class, node_id);
    });

    $('#node_edit_button_remove').on('click', function() {
        bootstrap.Modal.getInstance(document.getElementById('node_edit_modal')).hide();
        // Remove possible old confirm window
        $('#node_confirm_remove_modal').remove();
        // Create new modal
        $('#main').append($(
            '<div class="modal fade" tabindex="-1" id="node_confirm_remove_modal" data-bs-backdrop="static" data-bs-keyboard="true">' +
                '<div class="modal-dialog">' +
                    '<div class="modal-content">' +
                        '<div class="modal-header">' +
                            '<h5 class="modal-title">Remove node "' + node['name'] + '"?</h5>' +
                        '</div>' +
                        '<div class="modal-footer">' +
                            '<button id="node_confirm_remove_button_no" type="button" class="btn btn-secondary" data-bs-dismiss="modal">No</button>' +
                            '<button id="node_confirm_remove_button_yes" type="button" class="btn btn-danger btn-block">Yes</button>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
            '</div>'
        ));
        var modal = document.getElementById('node_confirm_remove_modal');
        var bootstrap_modal = new bootstrap.Modal(modal, {});
        bootstrap_modal.show();
        // Logic for removing
        $('#node_confirm_remove_button_yes').on('click', function() {
            $.ajax({
                url: '/api/v1/nodes/' + node_id + '/',
                method: 'DELETE',
                headers: {'X-CSRFToken': window.csrf_token},
            }).done(function() {
                bootstrap.Modal.getInstance(document.getElementById('node_confirm_remove_modal')).hide();
                delete UI.nodes[node_id];
                delete UI.nodes_from_server[node_id];
                var new_connections = {};
                for (var [connection_id, connection] of Object.entries(UI.connections)) {
                    if (connection.source != node_id && connection.dest != node_id) {
                        new_connections[connection_id] = connection;
                    }
                }
                UI.connections = new_connections;
                reconstructNodesAndConnectionsToUi();
            });
        });
    });

    var modal = document.getElementById('node_edit_modal');
    var bootstrap_modal = new bootstrap.Modal(modal, {});
    bootstrap_modal.show();
}

function createNodeCreationModal()
{
    // Remove possible old modal
    $('#node_edit_modal').remove();

    var logic_options = '';
    for (var [key, field] of Object.entries(UI.static_data.logics)) {
        var logic = UI.static_data.logics[key];
        logic_options += '<option value="' + key + '">' + logic.name + '</option>';
    }

    // Create new modal
    $('#main').append($(
        '<div class="modal fade" tabindex="-1" id="node_edit_modal" data-bs-backdrop="static" data-bs-keyboard="true">' +
            '<div class="modal-dialog">' +
                '<div class="modal-content">' +
                    '<div class="modal-header">' +
                        '<h5 class="modal-title">Create node</h5>' +
                    '</div>' +
                    '<div id="node_edit_modal_content" class="modal-body">' +
                        '<label for="logic_select" class="form-label">Type</label>' +
                        '<select id="logic_select" class="form-select">' +
                            '<option value="" selected>-</option>' +
                            logic_options +
                        '</select>' +
                        '<div id="logic_description" class="form-text"></div>' +
                    '</div>' +
                    '<div class="modal-footer">' +
                        '<button id="node_edit_button_cancel" type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>' +
                        '<button id="node_edit_button_proceed" type="button" class="btn btn-primary" disabled>Next</button>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>'
    ));
    var modal = document.getElementById('node_edit_modal');
    var bootstrap_modal = new bootstrap.Modal(modal, {});
    bootstrap_modal.show();

    // Select changing logic
    $('#logic_select').on('change', function() {
        const logic_class = $('#logic_select').val();
        if (logic_class) {
            $('#logic_description').text(UI.static_data.logics[logic_class].description);
            $('#node_edit_button_proceed').prop('disabled', false);
        } else {
            $('#logic_description').text('');
            $('#node_edit_button_proceed').prop('disabled', true);
        }
    });

    // Next button logic
    $('#node_edit_button_proceed').on('click', function() {
        const logic_class = $('#logic_select').val();

        // Remove old content
        $('#node_edit_button_proceed').remove();
        $('#node_edit_modal_content').empty();

        // Create new form
        $('#node_edit_modal_content').append($(generateNodeDetailsFormHtml(logic_class, null)));

        // Add save button
        $('#node_edit_button_cancel').after($('<button id="node_edit_button_proceed" type="button" class="btn btn-primary">Save</button>'));
        $('#node_edit_button_proceed').on('click', function() {
            submitNodeDetailsForm(logic_class, null);
        });
    });
}

function constructAndShowSettingsModal()
{
    // Remove possible old modal
    $('#settings_modal').remove();

    var countrycode_options = '';
    for (var [countrycode, country_data] of Object.entries(UI.static_data.countries)) {
        countrycode_options += '<option value="' + countrycode + '"';
        if (UI.settings.countrycode == countrycode) {
            countrycode_options += ' selected';
        }
        countrycode_options += '>' + country_data.name + '</option>';
    }

    var timezone_options = '';
    for (var timezone_i = 0; timezone_i < UI.static_data.timezones.length; ++ timezone_i) {
        var key_and_name = UI.static_data.timezones[timezone_i]
        timezone_options += '<option value="' + key_and_name[0] + '"';
        if (UI.settings.timezone == key_and_name[0]) {
            timezone_options += ' selected';
        }
        timezone_options += '>' + key_and_name[1] + '</option>';
    }

    const keyboard_close_allowed = !!(UI.settings.countrycode && UI.settings.timezone);

    // Create new modal
    $('#main').append($(
        '<div class="modal fade" tabindex="-1" id="settings_modal" data-bs-backdrop="static" data-bs-keyboard="' + keyboard_close_allowed + '">' +
            '<div class="modal-dialog">' +
                '<div class="modal-content">' +
                    '<div class="modal-header">' +
                        '<h5 class="modal-title">Settings</h5>' +
                    '</div>' +
                    '<div class="modal-body">' +
                        '<label for="settings_countrycode_select" class="form-label">Country</label>' +
                        '<select id="settings_countrycode_select" class="form-select">' +
                            '<option value="" selected>-</option>' +
                            countrycode_options +
                        '</select>' +
                        '<label for="settings_timezone_select" class="form-label">Timezone</label>' +
                        '<select id="settings_timezone_select" class="form-select">' +
                            '<option value="" selected>-</option>' +
                            timezone_options +
                        '</select>' +
                    '</div>' +
                    '<div class="modal-footer">' +
                        '<button id="settings_button_cancel" type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>' +
                        '<button id="settings_button_save" type="button" class="btn btn-primary" disabled>Save</button>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>'
    ));
    var modal = document.getElementById('settings_modal');
    var bootstrap_modal = new bootstrap.Modal(modal, {});
    bootstrap_modal.show();

    updateSettingsModalInputs();

    // Set up form logic
    $('#settings_countrycode_select').on('change', function() {
        updateSettingsModalInputs(false);
    });
    $('#settings_timezone_select').on('change', function() {
        updateSettingsModalInputs(false);
    });

    $('#settings_button_save').on('click', function() {
        const countrycode = $('#settings_countrycode_select').val();
        const timezone = $('#settings_timezone_select').val();

        updateSettingsModalInputs(true);

        saveVariables({
            'countrycode': countrycode,
            'timezone': timezone,
        }).then(
            function() {
                UI.settings['countrycode'] = countrycode;
                UI.settings['timezone'] = timezone;
                bootstrap.Modal.getInstance(document.getElementById('settings_modal')).hide();
            },
            function() {
                alert('Saving settings failed!');
                updateSettingsModalInputs(false);
            },
        );
    });
}

function updateSettingsModalInputs(force_all_disabled)
{
    // Check if cancel button should be enabled
    $('#settings_button_cancel').prop('disabled', force_all_disabled || !UI.settings.countrycode || !UI.settings.timezone);

    // Check if save button should be enabled
    $('#settings_button_save').prop('disabled', force_all_disabled || !$('#settings_countrycode_select').val() || !$('#settings_timezone_select').val());

    $('#settings_countrycode_select').prop('disabled', force_all_disabled);
    $('#settings_timezone_select').prop('disabled', force_all_disabled);
}

function makeSvgElement(tag, attrs)
{
    var elem = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (var key in attrs) {
        elem.setAttribute(key, attrs[key]);
    }
    return elem;
}

function startMovingNode(node_id, cursor_x, cursor_y)
{
    UI.moving_node_id = node_id;
    UI.moving_node_offset_x = cursor_x - UI.nodes[node_id].pos_x;
    UI.moving_node_offset_y = cursor_y - UI.nodes[node_id].pos_y;
    UI.moving_node_original_cursor_x = cursor_x;
    UI.moving_node_original_cursor_y = cursor_y;
    UI.moving_node_started = false;
}

function startMovingConnectionSource(node_id, key, cursor_x, cursor_y)
{
    // Try to find connection that begins from here
    for (var [connection_id, connection] of Object.entries(UI.connections)) {
        if (connection.source == node_id && connection.source_key == key) {
            UI.moving_connection_id = Number(connection_id);
            UI.moving_connection_source = true;
            UI.moving_connection_pos = [cursor_x, cursor_y];
            reconstructNodesAndConnectionsToUi();
            return;
        }
    }
    // If there was no connection, then start constructing a new one
    UI.adding_connection_source = node_id;
    UI.adding_connection_source_key = key;
    UI.adding_connection_pos = [cursor_x, cursor_y];
    UI.adding_connection_waiting_ajax = false;
}

function startMovingConnectionDestination(node_id, key, cursor_x, cursor_y)
{
    // Try to find connection that ends to here
    for (var [connection_id, connection] of Object.entries(UI.connections)) {
        if (connection.dest == node_id && connection.dest_key == key) {
            UI.moving_connection_id = Number(connection_id);
            UI.moving_connection_source = false;
            UI.moving_connection_pos = [cursor_x, cursor_y];
            reconstructNodesAndConnectionsToUi();
            return;
        }
    }
    // If there was no connection, then start constructing a new one
    UI.adding_connection_dest = node_id;
    UI.adding_connection_dest_key = key;
    UI.adding_connection_pos = [cursor_x, cursor_y];
    UI.adding_connection_waiting_ajax = false;
}

function handleMouseMove(event)
{
    if (UI.moving_node_id) {
        if (!UI.moving_node_started) {
            const diff_x = event.originalEvent.x - UI.moving_node_original_cursor_x;
            const diff_y = event.originalEvent.y - UI.moving_node_original_cursor_y;
            const distance = Math.sqrt(diff_x * diff_x + diff_y * diff_y);
            if (distance > 5) {
                UI.moving_node_started = true;
            }
        }
        if (UI.moving_node_started) {
            UI.nodes[UI.moving_node_id].pos_x = event.originalEvent.x - UI.moving_node_offset_x;
            UI.nodes[UI.moving_node_id].pos_y = event.originalEvent.y - UI.moving_node_offset_y;
            reconstructNodesAndConnectionsToUi();
        }
    } else if (UI.moving_connection_id) {
        UI.moving_connection_pos = [event.originalEvent.x, event.originalEvent.y];
        reconstructNodesAndConnectionsToUi();
    } else if ((UI.adding_connection_source || UI.adding_connection_dest) && !UI.adding_connection_waiting_ajax) {
        UI.adding_connection_pos = [event.originalEvent.x, event.originalEvent.y];
        reconstructNodesAndConnectionsToUi();
    }
}

function handleMouseUp(event)
{
    if (event.originalEvent.button == 0) {
        // Moving node
        if (UI.moving_node_id && UI.moving_node_started) {
            // Update position to server
            var new_pos_x = event.originalEvent.x - UI.moving_node_offset_x;
            var new_pos_y = event.originalEvent.y - UI.moving_node_offset_y;
            $.ajax({
                url: '/api/v1/nodes/' + UI.moving_node_id + '/',
                method: 'PATCH',
                headers: {'X-CSRFToken': window.csrf_token},
                data: JSON.stringify({
                    pos_x: new_pos_x,
                    pos_y: new_pos_y,
                }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
            });
            // Mark moving stopped
            UI.moving_node_id = null;
        }
        // Clicking node
        else if (UI.moving_node_id && !UI.moving_node_started) {
            constructAndShowNodeDetailsModal(UI.moving_node_id);
            UI.moving_node_id = null;
        }
        // Moving connection
        else if (UI.moving_connection_id) {
            var svg = document.getElementById('nodes_svg');
            // Check if any of the nodes is close enough this
            var nearest_distance = 20;
            var nearest_node_id = null;
            var nearest_key = null;
            for (var [node_id, node] of Object.entries(UI.nodes)) {
                if (UI.moving_connection_source) {
                    for (var output_i = 0; output_i < node.outputs.length; ++ output_i) {
                        const diff_x = node.pos_x + 200 - (event.originalEvent.x - svg.getBoundingClientRect().x);
                        const diff_y = node.pos_y + 32 + 12 * output_i - (event.originalEvent.y - svg.getBoundingClientRect().y);
                        const distance = Math.sqrt(diff_x * diff_x + diff_y * diff_y);
                        if (distance < nearest_distance) {
                            nearest_distance = distance;
                            nearest_node_id = node.id;
                            nearest_key = node.outputs[output_i];
                        }
                    }
                } else {
                    for (var input_i = 0; input_i < node.inputs.length; ++ input_i) {
                        const diff_x = node.pos_x - (event.originalEvent.x - svg.getBoundingClientRect().x);
                        const diff_y = node.pos_y + 32 + 12 * input_i - (event.originalEvent.y - svg.getBoundingClientRect().y);
                        const distance = Math.sqrt(diff_x * diff_x + diff_y * diff_y);
                        if (distance < nearest_distance) {
                            nearest_distance = distance;
                            nearest_node_id = node.id;
                            nearest_key = node.inputs[input_i];
                        }
                    }
                }
            }
            // If nearest node was found, then update the connection
            if (nearest_node_id) {
                var data = null;
                if (UI.moving_connection_source) {
                    UI.connections[UI.moving_connection_id].source = nearest_node_id;
                    UI.connections[UI.moving_connection_id].source_key = nearest_key;
                    data = {
                        source: nearest_node_id,
                        source_key: nearest_key,
                    };
                } else {
                    UI.connections[UI.moving_connection_id].dest = nearest_node_id;
                    UI.connections[UI.moving_connection_id].dest_key = nearest_key;
                    data = {
                        dest: nearest_node_id,
                        dest_key: nearest_key,
                    };
                }
                $.ajax({
                    url: '/api/v1/connections/' + UI.moving_connection_id + '/',
                    method: 'PATCH',
                    headers: {'X-CSRFToken': window.csrf_token},
                    data: JSON.stringify(data),
                    dataType: 'json',
                    contentType: 'application/json; charset=utf-8',
                });
            }
            // If no node was found, then remove the connection
            else {
                $.ajax({
                    url: '/api/v1/connections/' + UI.moving_connection_id + '/',
                    method: 'DELETE',
                    headers: {'X-CSRFToken': window.csrf_token},
                });
                delete UI.connections[UI.moving_connection_id];
            }

            UI.moving_connection_id = null;
            reconstructNodesAndConnectionsToUi();
        }
        // Adding a new connection from specific source to somewhere
        else if (UI.adding_connection_source) {
            var svg = document.getElementById('nodes_svg');
            // Check if any of the nodes is close enough this
            var nearest_distance = 20;
            var nearest_node_id = null;
            var nearest_key = null;
            for (var [node_id, node] of Object.entries(UI.nodes)) {
                for (var input_i = 0; input_i < node.inputs.length; ++ input_i) {
                    const diff_x = node.pos_x - (event.originalEvent.x - svg.getBoundingClientRect().x);
                    const diff_y = node.pos_y + 32 + 12 * input_i - (event.originalEvent.y - svg.getBoundingClientRect().y);
                    const distance = Math.sqrt(diff_x * diff_x + diff_y * diff_y);
                    if (distance < nearest_distance) {
                        nearest_distance = distance;
                        nearest_node_id = node.id;
                        nearest_key = node.inputs[input_i];
                    }
                }
            }
            // If nearest node was found, then create new connection
            if (nearest_node_id) {
                var data = {
                    source: UI.adding_connection_source,
                    source_key: UI.adding_connection_source_key,
                    dest: nearest_node_id,
                    dest_key: nearest_key,
                };
                $.ajax({
                    url: '/api/v1/connections/',
                    method: 'POST',
                    headers: {'X-CSRFToken': window.csrf_token},
                    data: JSON.stringify(data),
                    dataType: 'json',
                    contentType: 'application/json; charset=utf-8',
                }).then(
                    function(connection_data, text_status, request) {
                        UI.connections[connection_data.id] = connection_data;
                        UI.adding_connection_source = null;
                        reconstructNodesAndConnectionsToUi();
                    },
                    function(request, text_status, error_thrown) {
                        // If connection failed, then just give up
                        UI.adding_connection_source = null;
                        reconstructNodesAndConnectionsToUi();
                    },
                );
                // Mark ajax being waited
                UI.adding_connection_waiting_ajax = true;
            }
            // If nearest node was not found, then just cancel connection adding
            else {
                UI.adding_connection_source = null;
                reconstructNodesAndConnectionsToUi();
            }
        }
        // Adding a new connection to specific source from somewhere
        else if (UI.adding_connection_dest) {
            var svg = document.getElementById('nodes_svg');
            // Check if any of the nodes is close enough this
            var nearest_distance = 20;
            var nearest_node_id = null;
            var nearest_key = null;
            for (var [node_id, node] of Object.entries(UI.nodes)) {
                for (var output_i = 0; output_i < node.outputs.length; ++ output_i) {
                    const diff_x = node.pos_x + 200 - (event.originalEvent.x - svg.getBoundingClientRect().x);
                    const diff_y = node.pos_y + 32 + 12 * output_i - (event.originalEvent.y - svg.getBoundingClientRect().y);
                    const distance = Math.sqrt(diff_x * diff_x + diff_y * diff_y);
                    if (distance < nearest_distance) {
                        nearest_distance = distance;
                        nearest_node_id = node.id;
                        nearest_key = node.outputs[output_i];
                    }
                }
            }
            // If nearest node was found, then create new connection
            if (nearest_node_id) {
                var data = {
                    source: nearest_node_id,
                    source_key: nearest_key,
                    dest: UI.adding_connection_dest,
                    dest_key: UI.adding_connection_dest_key,
                };
                $.ajax({
                    url: '/api/v1/connections/',
                    method: 'POST',
                    headers: {'X-CSRFToken': window.csrf_token},
                    data: JSON.stringify(data),
                    dataType: 'json',
                    contentType: 'application/json; charset=utf-8',
                }).then(
                    function(connection_data, text_status, request) {
                        UI.connections[connection_data.id] = connection_data;
                        UI.adding_connection_dest = null;
                        reconstructNodesAndConnectionsToUi();
                    },
                    function(request, text_status, error_thrown) {
                        // If connection failed, then just give up
                        UI.adding_connection_dest = null;
                        reconstructNodesAndConnectionsToUi();
                    },
                );
                // Mark ajax being waited
                UI.adding_connection_waiting_ajax = true;
            }
            // If nearest node was not found, then just cancel connection adding
            else {
                UI.adding_connection_dest = null;
                reconstructNodesAndConnectionsToUi();
            }
        }
    }
}

function addCurve(svg, source_pos, dest_pos)
{
    var diff_x = dest_pos[0] - source_pos[0];
    var diff_y = dest_pos[1] - source_pos[1];
    const source_dest_distance = Math.sqrt(diff_x * diff_x + diff_y * diff_y);
    const curve_strength = source_dest_distance / 2;
    svg.appendChild(makeSvgElement('path', {
        d: 'M ' + source_pos[0] + ' ' + source_pos[1] + ' C ' + (source_pos[0] + curve_strength) + ' ' + source_pos[1] + ' ' + (dest_pos[0] - curve_strength) + ' ' + dest_pos[1] + ' ' + dest_pos[0] + ' ' + dest_pos[1],
        stroke: '#333',
        'stroke-width': '2',
        fill: 'transparent',
    }));
}

function arraysEqual(arr1, arr2)
{
    if (arr1.length != arr2.length) return false;
    for (var i = 0; i < arr1.length; ++ i) {
        if (arr1[i] != arr2[i]) return false;
    }
    return true;
}

function nodesEqual(node1, node2)
{
// TODO: What to do with settings and state?
    if (node1.name != node2.name) return false;
    if (node1.logic_class != node2.logic_class) return false;
    if (node1.pos_x != node2.pos_x) return false;
    if (node1.pos_y != node2.pos_y) return false;
    if (!arraysEqual(node1.inputs, node2.inputs)) return false;
    if (!arraysEqual(node1.outputs, node2.outputs)) return false;
    return true;
}

function connectionsEqual(connection1, connection2)
{
    if (connection1.source != connection2.source) return false;
    if (connection1.source_key != connection2.source_key) return false;
    if (connection1.dest != connection2.dest) return false;
    if (connection1.dest_key != connection2.dest_key) return false;
    return true;
}

function handleNewDataFromServer(nodes, connections)
{
    // Find out what nodes/connections are new or changed
    for (var [node_id, node] of Object.entries(nodes)) {
        if (!(node.id in UI.nodes_from_server)) {
            UI.nodes[node.id] = node;
        } else if (!nodesEqual(UI.nodes_from_server[node.id], nodes[node.id])) {
            UI.nodes[node.id] = node;
        }
    }
    for (var [connection_id, connection] of Object.entries(connections)) {
        if (!(connection.id in UI.connections_from_server)) {
            UI.connections[connection.id] = connection;
        } else if (!connectionsEqual(UI.connections_from_server[connection.id], connections[connection.id])) {
            UI.connections[connection.id] = connection;
        }
    }
    // Find out what nodes/connections are deleted
    for (var [node_id, node] of Object.entries(UI.nodes_from_server)) {
        if (!(node.id in nodes)) {
            delete UI.nodes[node.id];
        }
    }
    for (var [connection_id, connection] of Object.entries(UI.connections_from_server)) {
        if (!(connection.id in connections)) {
            delete UI.connections[connection.id];
        }
    }

    // Update UI
    reconstructNodesAndConnectionsToUi();

    // Finally store state of server to local memory
    UI.nodes_from_server = nodes;
    UI.connections_from_server = connections;
}

function constructUi()
{
    var svg = document.getElementById('main').appendChild(makeSvgElement('svg', {
        id: 'nodes_svg',
        width: '100%',
        height: '100%',
    }));
    svg.appendChild(makeSvgElement('style', {})).append(
        '.node_name {\n' +
        '    font: bold 16px arial;\n' +
        '    cursor: grab;\n' +
        '    pointer-events: none;\n' +
        '}\n' +
        '.input_output_name {\n' +
        '    font: bold 12px arial;\n' +
        '    pointer-events: none;\n' +
        '}\n' +
        '.node_rectangle {\n' +
        '    fill: #eee;\n' +
        '    stroke: #333;\n' +
        '    stroke-width: 2;\n' +
        '    cursor: grab;\n' +
        '}\n' +
        '.input_output_dot {\n' +
        '    fill: #fff;\n' +
        '    stroke: #333;\n' +
        '    stroke-width: 2;\n' +
        '}\n'
    );

    $('#nodes_svg').mousemove(handleMouseMove);
    $('#nodes_svg').mouseup(handleMouseUp);
}

function reconstructNodesAndConnectionsToUi()
{
    var svg = document.getElementById('nodes_svg');

    // Delete possible old graphics
    var nodes_svg = svg.getElementsByTagName('g');
    while (nodes_svg.length > 0) {
        nodes_svg[0].remove();
    }
    var nodes_svg = svg.getElementsByTagName('path');
    while (nodes_svg.length > 0) {
        nodes_svg[0].remove();
    }

    // Make a map for positions where connections should be connected to
    var input_output_poss = [];
    for (var [node_id, node] of Object.entries(UI.nodes)) {
        // Inputs
        for (var input_i = 0; input_i < node.inputs.length; ++ input_i) {
            input_output_poss[node.id + '_i_' + node.inputs[input_i]] = [node.pos_x + 0, node.pos_y + 32 + 12 * input_i];
        }
        // Outputs
        for (var output_i = 0; output_i < node.outputs.length; ++ output_i) {
            input_output_poss[node.id + '_o_' + node.outputs[output_i]] = [node.pos_x + 200, node.pos_y + 32 + 12 * output_i];
        }
    }

    // Construct connections
    for (var [connection_id, connection] of Object.entries(UI.connections)) {
        // Get source and destination positions
        var source_pos = input_output_poss[connection.source + '_o_' + connection.source_key];
        var dest_pos = input_output_poss[connection.dest + '_i_' + connection.dest_key];
        // If this connection is being dragged, then modify source or destination position
        if (UI.moving_connection_id == Number(connection_id)) {
            if (UI.moving_connection_source) {
                source_pos = [
                    UI.moving_connection_pos[0] - svg.getBoundingClientRect().x,
                    UI.moving_connection_pos[1] - svg.getBoundingClientRect().y,
                ]
            } else {
                dest_pos = [
                    UI.moving_connection_pos[0] - svg.getBoundingClientRect().x,
                    UI.moving_connection_pos[1] - svg.getBoundingClientRect().y,
                ]
            }
        }

        addCurve(svg, source_pos, dest_pos);
    }

    // If new connection is being added, then create a path for that too
    if (UI.adding_connection_source) {
        var source_pos = input_output_poss[UI.adding_connection_source + '_o_' + UI.adding_connection_source_key];
        var dest_pos = [
            UI.adding_connection_pos[0] - svg.getBoundingClientRect().x,
            UI.adding_connection_pos[1] - svg.getBoundingClientRect().y,
        ];
        addCurve(svg, source_pos, dest_pos);
    } else if (UI.adding_connection_dest) {
        var source_pos = [
            UI.adding_connection_pos[0] - svg.getBoundingClientRect().x,
            UI.adding_connection_pos[1] - svg.getBoundingClientRect().y,
        ];
        var dest_pos = input_output_poss[UI.adding_connection_dest + '_i_' + UI.adding_connection_dest_key];
        addCurve(svg, source_pos, dest_pos);
    }

    // Construct nodes
    for (var [node_id, node] of Object.entries(UI.nodes)) {
        // Group elements
        var node_svg = svg.appendChild(makeSvgElement('g', {
            transform: 'translate(' + node.pos_x + ' ' + node.pos_y + ')',
        }));
        // Rectangle
        var node_rect = node_svg.appendChild(makeSvgElement('rect', {
            width: 200,
            height: 150,
            rx: 4,
            ry: 4,
            class: 'node_rectangle',
        }));
// TODO: Why this is needed?
        const node_id2 = Number(node_id);
        $(node_rect).mousedown(function(event) {
            if (event.originalEvent.button == 0) {
                startMovingNode(node_id2, event.originalEvent.x, event.originalEvent.y);
            }
        });
        // Name
        node_svg.appendChild(makeSvgElement('text', {
            x: 100,
            y: 16,
            class: 'node_name',
            'text-anchor': 'middle',
        })).textContent = stripTags(node.name);
        // Inputs
        for (var input_i = 0; input_i < node.inputs.length; ++ input_i) {
            const input_key = node.inputs[input_i];
            // Dot
            var node_circle = node_svg.appendChild(makeSvgElement('circle', {
                cx: 0,
                cy: 32 + 12 * input_i,
                r: 5,
                class: 'input_output_dot',
            }));
            $(node_circle).mousedown(function(event) {
                if (event.originalEvent.button == 0) {
                    startMovingConnectionDestination(node_id2, input_key, event.originalEvent.x, event.originalEvent.y);
                }
            });
            // Text
            node_svg.appendChild(makeSvgElement('text', {
                x: 8,
                y: 36 + 12 * input_i,
                class: 'input_output_name',
            })).textContent = input_key;
        }
        // Outputs
        for (var output_i = 0; output_i < node.outputs.length; ++ output_i) {
            const output_key = node.outputs[output_i];
            // Dot
            var node_circle = node_svg.appendChild(makeSvgElement('circle', {
                cx: 200,
                cy: 32 + 12 * output_i,
                r: 5,
                class: 'input_output_dot',
            }));
            $(node_circle).mousedown(function(event) {
                if (event.originalEvent.button == 0) {
                    startMovingConnectionSource(node_id2, output_key, event.originalEvent.x, event.originalEvent.y);
                }
            });
            // Text
            node_svg.appendChild(makeSvgElement('text', {
                x: 200 - 8,
                y: 36 + 12 * output_i,
                class: 'input_output_name',
                'text-anchor': 'end',
            })).textContent = output_key;
        }
    }
}

function fetchDataAndUpdateUi()
{
    return new Promise(function(resolve, reject) {
        $.ajax({
            url: '/api/v1/nodes/',
        }).then(
            function(nodes_data, text_status, request) {
                $.ajax({ url: '/api/v1/connections/' }).then(
                    function(connections_data, text_status, request) {
                        // Convert arrays into objects
                        var nodes = {};
                        var connections = {};
                        nodes_data.forEach(function(node) {
                            nodes[node.id] = node;
                        })
                        connections_data.forEach(function(connection) {
                            connections[connection.id] = connection;
                        })

                        handleNewDataFromServer(nodes, connections);

                        resolve();
                    },
                    function(request, text_status, error_thrown) {
                        reject();
                    },
                );
            },
            function(request, text_status, error_thrown) {
                reject();
            },
        );
    });
}

function fetchVariables(names)
{
    const name = names[0];
    var names_except_first = names.slice(1);

    return new Promise(function(resolve, reject) {
        $.ajax({ url: '/api/v1/variables/' + names[0]}).then(
            function(variable_data, text_status, request) {
                const value = variable_data['value'];
                if (names_except_first.length > 0) {
                    fetchVariables(names_except_first).then(
                        function(results)
                        {
                            results[name] = value;
                            resolve(results);
                        },
                        function()
                        {
                            reject();
                        },
                    );
                } else {
                    var results = {};
                    results[name] = value;
                    resolve(results);
                }
            },
            function(request, text_status, error_thrown) {
                // If variable is not found. This is a minor error. It means we can continue checking others.
                if (request.status == 404) {
                    if (names_except_first.length > 0) {
                        fetchVariables(names_except_first).then(
                            function(results)
                            {
                                resolve(results);
                            },
                            function()
                            {
                                reject();
                            },
                        );
                    } else {
                        resolve({});
                    }
                } else {
                    reject();
                }
            }
        )
    });
}

function fetchSettings()
{
    fetchVariables(['countrycode', 'timezone']).then(
        function(result) {
            UI.settings = result;
            if (!UI.settings['countrycode'] || !UI.settings['timezone']) {
                constructAndShowSettingsModal();
            }
        },
        function() {
        },
    );
}

$(window).on('load', function() {

    constructUi();

    // Fetch static data
    fetchStaticData([
        ['/api/v1/logics/', 'logics'],
        ['/api/v1/countries/', 'countries'],
        ['/api/v1/timezones/', 'timezones'],
    ]).then(
        function() {
            // Now start fetching nodes data
            fetchDataAndUpdateUi().then(
                function() {
                    setInterval(function() {
                        fetchDataAndUpdateUi().then();
                    }, 5000);
                    fetchSettings();
                },
                function() {
                    setInterval(function() {
                        fetchDataAndUpdateUi().then();
                    }, 5000);
                    fetchSettings();
                },
            );
            // Set up button event
            $('#node_creation_button').on('click', createNodeCreationModal);
        },
        function() {
            alert('Fetching static data failed!');
        },
    );
});
