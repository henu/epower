UI = {};

UI.nodes_from_server = {};
UI.connections_from_server = {};
UI.nodes = {};
UI.connections = {};

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
}

function handleMouseMove(event)
{
    if (UI.moving_node_id) {
        UI.nodes[UI.moving_node_id].pos_x = event.originalEvent.x - UI.moving_node_offset_x;
        UI.nodes[UI.moving_node_id].pos_y = event.originalEvent.y - UI.moving_node_offset_y;
        reconstructNodesAndConnectionsToUi();
    } else if (UI.moving_connection_id) {
        UI.moving_connection_pos = [event.originalEvent.x, event.originalEvent.y];
        reconstructNodesAndConnectionsToUi();
    }
}

function handleMouseUp(event)
{
    if (event.originalEvent.button == 0) {
        if (UI.moving_node_id) {
            // Update position to server
            var new_pos_x = event.originalEvent.x - UI.moving_node_offset_x;
            var new_pos_y = event.originalEvent.y - UI.moving_node_offset_y;
            $.ajax({
                url: '/api/v1/nodes/' + UI.moving_node_id + '/',
                method: 'PATCH',
                headers: {'X-CSRFToken': window.csrf_token},
                data: {
                    pos_x: new_pos_x,
                    pos_y: new_pos_y,
                },
            });
            // Mark moving stopped
            UI.moving_node_id = null;
        } else if (UI.moving_connection_id) {
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
                    data: data,
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
    }
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
        height: '640',
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
        })).textContent = node.name;
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

$(window).on('load', function() {

    constructUi();

    // Do the initial fetching of node data
    fetchDataAndUpdateUi().then(
        function() {
            setInterval(function() {
                fetchDataAndUpdateUi().then();
            }, 5000);
        },
        function() {
            setInterval(function() {
                fetchDataAndUpdateUi().then();
            }, 5000);
        },
    );
});
