function makeSvgElement(tag, attrs)
{
    var elem = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (var key in attrs) {
        elem.setAttribute(key, attrs[key]);
    }
    return elem;
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
        '}\n' +
        '.input_output_name {\n' +
        '    font: bold 12px arial;\n' +
        '}\n'
    );
}

function updateNodes(data)
{
    var svg = document.getElementById('nodes_svg');

    // Delete possible old graphics
    var nodes_svg = svg.getElementsByTagName('g');
    while (nodes_svg.length > 0) {
        nodes_svg[0].remove();
    }

    // Use data to construct or update SVG elements
    data.forEach(function(node) {
        // Group elements
        var node_svg = svg.appendChild(makeSvgElement('g', {
            id: 'node_svg_' + node.id,
            transform: 'translate(' + node.pos_x + ' ' + node.pos_y + ')',
        }));
        // Rectangle
        node_svg.appendChild(makeSvgElement('rect', {
            width: 200,
            height: 150,
            rx: 4,
            ry: 4,
            style: 'fill:#eee;stroke:#333;stroke-width:2;',
        }));
        // Name
        node_svg.appendChild(makeSvgElement('text', {
            x: 100,
            y: 16,
            class: 'node_name',
            'text-anchor': 'middle',
        })).textContent = node.name;
        // Inputs
        for (var input_i = 0; input_i < node.inputs.length; ++ input_i) {
            // Dot
            node_svg.appendChild(makeSvgElement('circle', {
                cx: 0,
                cy: 32 + 12 * input_i,
                r: 5,
                style: 'fill:#fff;stroke:#333;stroke-width:2;',
            }));
            // Text
            node_svg.appendChild(makeSvgElement('text', {
                x: 8,
                y: 36 + 12 * input_i,
                class: 'input_output_name',
            })).textContent = node.inputs[input_i];
        }
        // Outputs
        for (var output_i = 0; output_i < node.outputs.length; ++ output_i) {
            // Dot
            node_svg.appendChild(makeSvgElement('circle', {
                cx: 200,
                cy: 32 + 12 * output_i,
                r: 5,
                style: 'fill:#fff;stroke:#333;stroke-width:2;',
            }));
            // Text
            node_svg.appendChild(makeSvgElement('text', {
                x: 200 - 8,
                y: 36 + 12 * output_i,
                class: 'input_output_name',
                'text-anchor': 'end',
            })).textContent = node.outputs[output_i];
        }
    });
}

function fetchAndUpdateNodes()
{
    $.ajax({
        url: '/api/v1/nodes/',
        success: function(data, text_status, request) {
            updateNodes(data);
        },
    });
}

function initialNodeFetchAndUpdate()
{
    $.ajax({
        url: '/api/v1/nodes/',
        success: function(data, text_status, request) {
            updateNodes(data);
        },
        complete: function(request, test_status) {
            setInterval(fetchAndUpdateNodes, 5000);
        },
    });
}

$(window).on('load', function() {

    constructUi();

    // Do the initial fetching of node data
    initialNodeFetchAndUpdate();

});
