// Test file with common JavaScript errors for testing the AI Error Translator

// TypeError examples
const data = undefined;
const result = data.map(item => item.name); // TypeError: Cannot read property 'map' of undefined

const user = null;
console.log(user.name); // TypeError: Cannot read property 'name' of null

// ReferenceError examples
console.log(undefinedVariable); // ReferenceError: undefinedVariable is not defined

// SyntaxError examples
const obj = {
    name: "test"
    age: 25  // Missing comma - SyntaxError
};

// Function errors
function processUsers(users) {
    return users.filter(user => user.active).map(user => user.name);
}
processUsers(null); // TypeError: Cannot read property 'filter' of null

// Async errors
async function fetchData() {
    const response = await fetch('/api/data');
    const data = await response.json();
    return data.results.map(item => item.id); // Potential TypeError if results is undefined
}

// Array errors
const numbers = [1, 2, 3];
console.log(numbers[10].toString()); // TypeError: Cannot read property 'toString' of undefined
