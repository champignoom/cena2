#include <iostream>
#include <fstream>
using namespace std;

int main() {
	ifstream fin("plus.in");
	ofstream fout("plus.out");
	cin.rdbuf(fin.rdbuf());
	cout.rdbuf(fout.rdbuf());
	int a, b;
	cin >>a >>b;
	cout <<a+b <<endl;
}
