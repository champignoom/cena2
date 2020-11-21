#include <iostream>
#include <fstream>
#include <thread>
using namespace std;

int main() {
	ifstream fin("minus.in");
	ofstream fout("minus.out");
	cin.rdbuf(fin.rdbuf());
	cout.rdbuf(fout.rdbuf());
	int a, b;
	cin >>a >>b;
	// this_thread::sleep_for(0.2s);
	if (b%2 == 0) {
		cout <<0 <<endl;
	} else if (b%3==0) {
		cout <<a/(b-b) <<endl;
	} else {
		cout <<a-b <<endl;
	}
}
